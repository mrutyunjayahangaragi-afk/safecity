"""
SafeRoute AI — Crowd Repository
==================================
Data access layer for crowd density information.

Priority chain (mirrors traffic_repository / weather_repository)
----------------------------------------------------------------
1. Supabase real-time tables  (live, when SUPABASE_URL / SUPABASE_KEY set)
2. Local crowd_dataset.csv    (synthetic fallback, always available)

Supabase tables
---------------
  crowd_density_reports  — user / sensor / CCTV crowd observations
  crowd_density_history  — historical crowd snapshots

Future integration hooks
------------------------
  get_point_crowd()  → replace body with Google Popular Times API call
  get_crowd_for_hour() → replace with event-management API or IoT feed
  No other file needs to change.
"""

import os
import logging
from datetime import datetime, timezone
from typing   import List, Optional, Dict

import pandas as pd
import numpy  as np

logger = logging.getLogger(__name__)


# ─── .env loader (same pattern as traffic/weather repositories) ───────────────
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

_load_env()


# ─── Supabase client ──────────────────────────────────────────────────────────
_supabase       = None
_supabase_ready = False

def _init_supabase() -> bool:
    global _supabase, _supabase_ready
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return False
    try:
        from supabase import create_client
        _supabase       = create_client(url, key)
        _supabase_ready = True
        logger.info("✅ Crowd repo: Supabase connected")
        return True
    except Exception as e:
        logger.warning(f"Crowd repo: Supabase unavailable ({e}) — local fallback")
        return False

_supabase_ready = _init_supabase()


# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE      = os.path.dirname(os.path.abspath(__file__))
_DATA_ROOT = os.path.join(_BASE, "../data")

def _crowd_csv_path(state_key: str = "karnataka", city_key: str = "bengaluru") -> str:
    return os.path.join(_DATA_ROOT, state_key, city_key, "crowd_dataset.csv")


# ─── In-memory caches ─────────────────────────────────────────────────────────
_crowd_df_cache:      Dict[str, pd.DataFrame] = {}
_crowd_reports:       List[dict] = []
_crowd_history:       List[dict] = []


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL DATASET OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_crowd_data(state_key: str = "karnataka", city_key: str = "bengaluru") -> pd.DataFrame:
    """Load and cache the crowd dataset for a city."""
    cache_key = f"{state_key}/{city_key}"
    if cache_key in _crowd_df_cache:
        return _crowd_df_cache[cache_key]

    path = _crowd_csv_path(state_key, city_key)
    if not os.path.exists(path):
        logger.warning(f"Crowd dataset not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    _crowd_df_cache[cache_key] = df
    logger.info(f"✅ Loaded {len(df):,} crowd records for {city_key}")
    return df


def get_crowd_for_hour(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> pd.DataFrame:
    """Return crowd records for a given hour, averaged across days."""
    df = load_crowd_data(state_key, city_key)
    if df.empty:
        return df

    hourly = df[df["hour"] == hour].copy()
    agg = (
        hourly.groupby(["area", "zone_type"])
        .agg(
            latitude          = ("latitude",          "mean"),
            longitude         = ("longitude",         "mean"),
            crowd_score       = ("crowd_score",       "mean"),
            estimated_people  = ("estimated_people",  "mean"),
            capacity          = ("capacity",          "first"),
            utilisation_pct   = ("utilisation_pct",   "mean"),
            has_metro         = ("has_metro",         "first"),
            bus_stops_nearby  = ("bus_stops_nearby",  "first"),
            isolation_risk    = ("isolation_risk",    "mean"),
            overcrowd_risk    = ("overcrowd_risk",    "mean"),
        )
        .reset_index()
        .round(3)
    )

    # Add crowd_level based on averaged score
    def _level(s):
        if s < 0.25:  return "Low"
        if s < 0.55:  return "Moderate"
        if s < 0.80:  return "High"
        return "Extreme"

    agg["crowd_level"] = agg["crowd_score"].apply(_level)
    agg["estimated_people"] = agg["estimated_people"].astype(int)
    return agg


def get_point_crowd(
    lat: float,
    lon: float,
    hour: int,
    radius_deg: float = 0.025,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """
    Return crowd data for the zone nearest to (lat, lon) at given hour.
    Falls back to synthetic estimate when no nearby record found.

    INTEGRATION HOOK: Replace the body of this function with a call to
    Google Popular Times API, an IoT sensor feed, or CCTV analytics
    without changing any other file.
    """
    df = get_crowd_for_hour(hour, state_key, city_key)
    if df.empty:
        return _synthetic_crowd(lat, lon, hour)

    dists = np.sqrt((df["latitude"] - lat) ** 2 + (df["longitude"] - lon) ** 2)
    idx   = int(dists.idxmin())

    if dists.iloc[idx] > radius_deg:
        return _synthetic_crowd(lat, lon, hour)

    row = df.iloc[idx]
    return {
        "area":              row["area"],
        "zone_type":         row["zone_type"],
        "crowd_score":       round(float(row["crowd_score"]), 3),
        "crowd_level":       row["crowd_level"],
        "estimated_people":  int(row["estimated_people"]),
        "capacity":          int(row["capacity"]),
        "utilisation_pct":   round(float(row["utilisation_pct"]), 1),
        "has_metro":         bool(row["has_metro"]),
        "bus_stops_nearby":  int(row["bus_stops_nearby"]),
        "isolation_risk":    round(float(row["isolation_risk"]), 3),
        "overcrowd_risk":    round(float(row["overcrowd_risk"]), 3),
        "data_source":       "local_dataset",
        "hour":              hour,
    }


def _synthetic_crowd(lat: float, lon: float, hour: int) -> dict:
    """Plausible crowd estimate when no dataset record is nearby."""
    is_night  = hour >= 20 or hour < 6
    is_peak   = (7 <= hour <= 10) or (17 <= hour <= 21)
    base      = 0.55 if is_peak else (0.12 if is_night else 0.35)
    score     = float(np.clip(base + np.random.uniform(-0.08, 0.08), 0.0, 1.0))

    def _level(s):
        if s < 0.25:  return "Low"
        if s < 0.55:  return "Moderate"
        if s < 0.80:  return "High"
        return "Extreme"

    return {
        "area":              "unknown",
        "zone_type":         "mixed",
        "crowd_score":       round(score, 3),
        "crowd_level":       _level(score),
        "estimated_people":  max(5, int(3000 * score)),
        "capacity":          3000,
        "utilisation_pct":   round(score * 100, 1),
        "has_metro":         False,
        "bus_stops_nearby":  3,
        "isolation_risk":    round(float(np.clip((1 - score) * (0.5 if is_night else 0.2), 0, 1)), 3),
        "overcrowd_risk":    round(float(np.clip(score * 0.8, 0, 1)), 3),
        "data_source":       "synthetic_estimate",
        "hour":              hour,
    }


def get_crowd_heatmap(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Return [{lat, lon, crowd_score, crowd_level, area, people}, ...] for map layer."""
    df = get_crowd_for_hour(hour, state_key, city_key)
    if df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            "lat":              round(float(row["latitude"]), 6),
            "lon":              round(float(row["longitude"]), 6),
            "crowd_score":      round(float(row["crowd_score"]), 3),
            "crowd_level":      row["crowd_level"],
            "estimated_people": int(row["estimated_people"]),
            "area":             row["area"],
            "zone_type":        row["zone_type"],
            "utilisation_pct":  round(float(row["utilisation_pct"]), 1),
            "isolation_risk":   round(float(row["isolation_risk"]), 3),
            "overcrowd_risk":   round(float(row["overcrowd_risk"]), 3),
        })
    return result


def get_crowd_stats(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Aggregated crowd statistics for analytics dashboard."""
    df = get_crowd_for_hour(hour, state_key, city_key)
    if df.empty:
        return {}

    most_crowded  = df.nlargest(5, "crowd_score")[["area","crowd_level","estimated_people","crowd_score"]].to_dict("records")
    least_crowded = df.nsmallest(5, "crowd_score")[["area","crowd_level","estimated_people","crowd_score"]].to_dict("records")

    return {
        "avg_crowd_score":   round(float(df["crowd_score"].mean()), 3),
        "avg_people":        int(df["estimated_people"].mean()),
        "total_people":      int(df["estimated_people"].sum()),
        "most_crowded":      most_crowded,
        "least_crowded":     least_crowded,
        "level_distribution": df["crowd_level"].value_counts().to_dict(),
        "peak_zones":        int((df["crowd_level"].isin(["High","Extreme"])).sum()),
        "total_zones":       len(df),
        "hour":              hour,
    }


def get_crowd_daily_trend(
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Average crowd metrics by hour — for daily trend chart."""
    df = load_crowd_data(state_key, city_key)
    if df.empty:
        return []
    trend = (
        df.groupby("hour")
        .agg(
            avg_crowd_score  = ("crowd_score",      "mean"),
            avg_people       = ("estimated_people", "mean"),
            avg_isolation    = ("isolation_risk",   "mean"),
            avg_overcrowd    = ("overcrowd_risk",   "mean"),
        )
        .reset_index()
        .round(3)
    )
    return trend.to_dict("records")


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE OPERATIONS (local fallback on every method)
# ═══════════════════════════════════════════════════════════════════════════════

def submit_crowd_report(report: dict) -> dict:
    """Store a community or sensor crowd density report."""
    entry = {
        "id":               len(_crowd_reports) + 1,
        "latitude":         report.get("latitude"),
        "longitude":        report.get("longitude"),
        "crowd_level":      report.get("crowd_level", "Moderate"),
        "crowd_score":      report.get("crowd_score", 0.5),
        "estimated_people": report.get("estimated_people", 100),
        "source":           report.get("source", "community"),
        "created_at":       datetime.now(timezone.utc).isoformat(),
    }

    if _supabase_ready and _supabase:
        try:
            _supabase.table("crowd_density_reports").insert(entry).execute()
            entry["supabase_source"] = "supabase"
            return entry
        except Exception as e:
            logger.warning(f"Supabase crowd insert failed: {e}")

    _crowd_reports.append(entry)
    entry["supabase_source"] = "local"
    return entry


def get_crowd_reports(limit: int = 100) -> List[dict]:
    """Fetch recent crowd density reports."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("crowd_density_reports")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Supabase crowd fetch failed: {e}")
    return list(reversed(_crowd_reports))[-limit:]


def get_supabase_status() -> dict:
    return {
        "connected": _supabase_ready,
        "mode":      "realtime" if _supabase_ready else "local_fallback",
    }
