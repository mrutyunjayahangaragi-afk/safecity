"""
SafeRoute AI — Safety Scoring Engine
City-agnostic: center point used for lighting heuristic is dynamic.
Bengaluru defaults preserved for full backward compatibility.

The original formula remains intact, but the engine now also uses the enriched
crime dataset when available so route comparison can reflect real environmental
features such as lighting, CCTV coverage, crowd density, police proximity, and
traffic congestion.
"""

import numpy as np
from typing import Optional
import pandas as pd

from data_processing import get_processed_dataset, time_risk_factor

# ─── Weight constants ──────────────────────────────────────────────────────────
W_CRIME    = 0.40
W_LIGHT    = 0.20
W_CCTV     = 0.20
W_CROWD    = 0.10
W_TIME     = 0.10

# ─── Precomputed density grid (loaded at startup) ─────────────────────────────
_density_grid: list = []
_processed_df: Optional[pd.DataFrame] = None

# City center used for lighting heuristic (set dynamically via set_city_center)
_city_center_lat: float = 12.9716
_city_center_lon: float = 77.5946


def load_density_grid(grid: list):
    """Called by app.py after computing density from crime data."""
    global _density_grid
    _density_grid = grid
    print(f"Safety engine loaded {len(grid)} density cells")


def load_processed_dataframe(df: pd.DataFrame):
    """Attach the enriched crime dataset so safety scoring can use local context."""
    global _processed_df
    _processed_df = df.copy() if df is not None else None
    print("Safety engine loaded enriched route context")


def set_city_center(lat: float, lon: float):
    """Update the city center used by the lighting heuristic."""
    global _city_center_lat, _city_center_lon
    _city_center_lat = lat
    _city_center_lon = lon
    print(f"Safety engine city center -> ({lat}, {lon})")


def _nearest_density(lat: float, lon: float) -> float:
    """Look up crime density for the closest grid cell."""
    if not _density_grid:
        return 0.5

    best_d = float("inf")
    best_v = 0.5
    for cell in _density_grid:
        d = (cell["lat"] - lat) ** 2 + (cell["lon"] - lon) ** 2
        if d < best_d:
            best_d = d
            best_v = cell["density"]
    return best_v


def _nearest_context(lat: float, lon: float) -> Optional[dict]:
    """Return the nearest enriched record from the processed dataset when available."""
    if _processed_df is None or _processed_df.empty:
        return None

    coords = _processed_df[["latitude", "longitude"]].to_numpy()
    diffs = np.sqrt((coords[:, 0] - lat) ** 2 + (coords[:, 1] - lon) ** 2)
    idx = int(np.argmin(diffs))
    row = _processed_df.iloc[idx]
    return row.to_dict()


# ─── Point-level safety score ─────────────────────────────────────────────────
def compute_safety_score(
    lat: float,
    lon: float,
    hour: int,
    lighting_score: Optional[float] = None,
    cctv_score: Optional[float] = None,
    crowd_density: Optional[float] = None,
) -> dict:
    """Return a composite safety risk score and component breakdown."""
    crime_density = _nearest_density(lat, lon)
    time_risk = time_risk_factor(hour)

    context = _nearest_context(lat, lon)
    if context is not None:
        if lighting_score is None:
            lighting_score = float(context.get("lighting_score", 0.5))
        if cctv_score is None:
            cctv_score = float(context.get("cctv_score", 0.5))
        if crowd_density is None:
            crowd_density = float(context.get("crowd_density", 0.5))

    if lighting_score is None:
        dist_center = np.sqrt((lat - _city_center_lat) ** 2 + (lon - _city_center_lon) ** 2)
        lighting_score = max(0.1, 1.0 - dist_center * 8)

    if cctv_score is None:
        cctv_score = max(0.05, lighting_score * 0.7 + np.random.uniform(-0.1, 0.1))

    if crowd_density is None:
        crowd_density = max(0.1, 0.8 - time_risk * 0.5)

    lighting_score = float(np.clip(lighting_score, 0.0, 1.0))
    cctv_score = float(np.clip(cctv_score, 0.0, 1.0))
    crowd_density = float(np.clip(crowd_density, 0.0, 1.0))

    score = (
        W_CRIME * crime_density +
        W_LIGHT * (1 - lighting_score) +
        W_CCTV * (1 - cctv_score) +
        W_CROWD * (1 - crowd_density) +
        W_TIME * time_risk
    )

    if context is not None:
        def _get_val(key, default_val):
            v = context.get(key, default_val)
            return default_val if pd.isna(v) else v
            
        traffic_congestion = float(np.clip(_get_val("traffic_congestion", 0.4), 0.0, 1.0))
        road_condition = float(np.clip(_get_val("road_condition", 0.5), 0.0, 1.0))
        police_proximity = float(np.clip(_get_val("police_proximity", 0.5), 0.0, 1.0))
        weather_impact = float(np.clip(_get_val("weather_impact", 0.2), 0.0, 1.0))
        road_closure = float(1.0 if _get_val("road_closure", 0) else 0.0)

        score += 0.04 * (1 - police_proximity)
        score += 0.03 * traffic_congestion
        score += 0.03 * (1 - road_condition)
        score += 0.02 * weather_impact
        score += 0.02 * road_closure

    score = float(np.clip(score, 0.0, 1.0))

    if score < 0.30:
        risk_level = "LOW"
    elif score < 0.55:
        risk_level = "MEDIUM"
    elif score < 0.75:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    return {
        "score": round(score, 4),
        "score_100": round(score * 100, 1),
        "crime_density": round(crime_density, 4),
        "lighting": round(lighting_score, 4),
        "cctv": round(cctv_score, 4),
        "crowd": round(crowd_density, 4),
        "time_risk": round(time_risk, 4),
        "risk_level": risk_level,
    }


# ─── Segment-level safety score ───────────────────────────────────────────────
def segment_safety_score(
    p1: tuple,
    p2: tuple,
    hour: int,
) -> float:
    """Return the averaged risk score for a road segment."""
    mid_lat = (p1[0] + p2[0]) / 2
    mid_lon = (p1[1] + p2[1]) / 2
    result = compute_safety_score(mid_lat, mid_lon, hour)
    return result["score"]
