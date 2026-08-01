"""
SafeRoute AI — Data Processing Module
Cleans crime data, clusters hotspots, computes density grids,
and enriches the dataset with road-environment features used by the route engine.
"""

import os
import json
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import MinMaxScaler

# Legacy default path — kept for backward compatibility
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/bangalore_crime_dataset.csv")

_PROCESSED_CACHE = {}


# ─── Load & clean dataset ─────────────────────────────────────────────────────
def load_and_clean(
    path: str = DATA_PATH,
    bbox: tuple = (12.80, 13.15, 77.45, 77.80),
) -> pd.DataFrame:
    """Load and clean a crime dataset for any city."""
    df = pd.read_csv(path)

    df.dropna(subset=["latitude", "longitude", "crime_severity"], inplace=True)

    min_lat, max_lat, min_lon, max_lon = bbox
    df = df[
        (df["latitude"].between(min_lat, max_lat)) &
        (df["longitude"].between(min_lon, max_lon))
    ].copy()

    scaler = MinMaxScaler()
    df["severity_norm"] = scaler.fit_transform(df[["crime_severity"]])

    if "hour" not in df.columns:
        df["hour"] = pd.to_datetime(df["time"], format="%H:%M", errors="coerce").dt.hour

    df["is_night"] = ((df["hour"] >= 20) | (df["hour"] < 6)).astype(int)

    print(f"Loaded {len(df)} clean crime records")
    return df


# ─── DBSCAN hotspot clustering ────────────────────────────────────────────────
def cluster_hotspots(df: pd.DataFrame, eps_km: float = 0.5, min_samples: int = 8):
    """Cluster crime incidents into hotspots and return a summary table."""
    coords = df[["latitude", "longitude"]].values
    eps_deg = eps_km / 111.0

    db = DBSCAN(eps=eps_deg, min_samples=min_samples, algorithm="ball_tree", metric="haversine")
    df = df.copy()
    df["cluster_id"] = db.fit_predict(np.radians(coords))

    valid = df[df["cluster_id"] >= 0]
    summary = (
        valid.groupby("cluster_id")
        .agg(
            lat=("latitude", "mean"),
            lon=("longitude", "mean"),
            count=("crime_type", "count"),
            avg_severity=("severity_norm", "mean"),
        )
        .reset_index()
    )
    print(f"Detected {len(summary)} crime hotspot clusters")
    return df, summary


# ─── Enrich dataset with road-environment context ────────────────────────────
def get_processed_dataset(path: str = DATA_PATH, bbox: tuple = (12.80, 13.15, 77.45, 77.80)) -> pd.DataFrame:
    """Return a cached, enriched dataset with derived route-planning features."""
    cache_key = (path, bbox)
    if cache_key in _PROCESSED_CACHE:
        return _PROCESSED_CACHE[cache_key]

    df = load_and_clean(path, bbox)
    df, _ = cluster_hotspots(df, eps_km=0.6, min_samples=8)

    df = df.reset_index(drop=True)
    _hc = df.groupby("cluster_id").size()
    df["hotspot_score"] = df["cluster_id"].map(_hc).fillna(0)
    hotspot_scale = max(float(df["hotspot_score"].max()), 1.0)
    df["hotspot_score"] = (df["hotspot_score"] / hotspot_scale).astype(float)

    df["crime_density"] = np.clip(0.55 * df["severity_norm"] + 0.45 * df["hotspot_score"], 0.0, 1.0)
    df["street_lighting"] = np.clip(df.get("lighting_score", 0.5), 0.0, 1.0)
    df["cctv_coverage"] = np.clip(df.get("cctv_score", 0.5), 0.0, 1.0)
    df["crowd_density"] = np.clip(df.get("crowd_density", 0.5), 0.0, 1.0)
    df["police_proximity"] = np.clip(df.get("police_proximity", 0.5), 0.0, 1.0)

    hour = df["hour"].fillna(22)
    congestion = (
        ((hour.between(7, 9)) | (hour.between(17, 21))).astype(float) * 0.55
        + df["is_night"].astype(float) * 0.20
        + 0.10
    )
    df["traffic_congestion"] = np.clip(congestion, 0.0, 1.0)

    df["road_condition"] = np.clip(0.35 + 0.35 * df["street_lighting"] + 0.30 * df["cctv_coverage"], 0.0, 1.0)
    df["road_type"] = np.where(hour.between(20, 23), "night", "mixed")
    df["weather_impact"] = np.clip(0.08 + 0.04 * df["is_night"].astype(float) + 0.03 * ((hour.between(0, 6)) | (hour.between(20, 23))).astype(float), 0.0, 1.0)
    df["road_closure"] = 0
    df["hospital_proximity"] = np.clip(0.35 + 0.45 * (1 - df["crime_density"]), 0.0, 1.0)
    df["time_risk"] = df["hour"].map(time_risk_factor).fillna(0.5)

    _PROCESSED_CACHE[cache_key] = df
    print(f"Enriched dataset with route-planning features ({len(df)} records)")
    return df


# ─── Grid-based crime density map ─────────────────────────────────────────────
def compute_density_grid(df: pd.DataFrame, resolution: float = 0.01) -> dict:
    """Divide the city into grid cells and compute crime density per cell."""
    df = df.copy()
    df["grid_lat"] = (df["latitude"] / resolution).round() * resolution
    df["grid_lon"] = (df["longitude"] / resolution).round() * resolution

    grid = (
        df.groupby(["grid_lat", "grid_lon"])
        .agg(
            crime_count=("crime_type", "count"),
            avg_severity=("severity_norm", "mean"),
        )
        .reset_index()
    )

    max_count = grid["crime_count"].max()
    grid["density"] = (
        0.6 * grid["crime_count"] / max_count +
        0.4 * grid["avg_severity"]
    ).round(4)

    heatmap_data = grid[["grid_lat", "grid_lon", "density"]].rename(
        columns={"grid_lat": "lat", "grid_lon": "lon"}
    ).to_dict(orient="records")

    print(f"Computed density for {len(heatmap_data)} grid cells")
    return heatmap_data


# ─── Time-based risk factor ────────────────────────────────────────────────────
def time_risk_factor(hour: int) -> float:
    """Return a risk multiplier 0–1 based on the hour of day."""
    risk_map = {
        0: 0.95, 1: 0.98, 2: 0.99, 3: 1.0,  4: 0.90, 5: 0.75,
        6: 0.55, 7: 0.40, 8: 0.35, 9: 0.30, 10: 0.28, 11: 0.25,
        12: 0.30, 13: 0.28, 14: 0.25, 15: 0.28, 16: 0.35, 17: 0.45,
        18: 0.60, 19: 0.72, 20: 0.82, 21: 0.88, 22: 0.92, 23: 0.94,
    }
    return risk_map.get(hour % 24, 0.5)


if __name__ == "__main__":
    df = load_and_clean()
    df, clusters = cluster_hotspots(df)
    grid = compute_density_grid(df)
    print(clusters.head())
