"""
SafeRoute AI — Weather Repository
====================================
Data access layer for weather information.

Priority chain (identical pattern to traffic_repository)
---------------------------------------------------------
1. Supabase real-time tables  (live, when SUPABASE_URL / SUPABASE_KEY set)
2. Local weather_dataset.csv  (synthetic fallback, always available)

Supabase tables
---------------
  weather_reports      — user / sensor submitted weather observations
  road_weather_alerts  — road-specific weather alerts (flood, fog, etc.)
  weather_history      — historical weather snapshots

Adding a live weather API (OpenWeatherMap, IMD, AccuWeather):
  Override get_current_weather() to call the external API.
  The rest of the system requires no changes.
"""

import os
import logging
from datetime import datetime, timezone
from typing   import List, Optional, Dict

import pandas as pd
import numpy  as np

logger = logging.getLogger(__name__)

# ─── Env loading (reuses same .env as traffic_repository) ─────────────────────
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

# ─── Supabase client (shared connection, optional) ────────────────────────────
_supabase = None

def _init_supabase():
    global _supabase
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return False
    try:
        from supabase import create_client
        _supabase = create_client(url, key)
        logger.info("✅ Weather repo: Supabase connected")
        return True
    except Exception as e:
        logger.warning(f"Weather repo: Supabase unavailable ({e}) — local fallback")
        return False

_supabase_ready = _init_supabase()

# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE      = os.path.dirname(os.path.abspath(__file__))
_DATA_ROOT = os.path.join(_BASE, "../data")

def _weather_csv_path(state_key: str = "karnataka", city_key: str = "bengaluru") -> str:
    return os.path.join(_DATA_ROOT, state_key, city_key, "weather_dataset.csv")

# ─── In-memory caches ─────────────────────────────────────────────────────────
_weather_df_cache: Dict[str, pd.DataFrame] = {}
_weather_reports:  List[dict] = []
_road_weather_alerts: List[dict] = []
_weather_history:  List[dict] = []


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL DATASET OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_weather_data(state_key: str = "karnataka", city_key: str = "bengaluru") -> pd.DataFrame:
    """Load and cache the weather dataset for a city."""
    cache_key = f"{state_key}/{city_key}"
    if cache_key in _weather_df_cache:
        return _weather_df_cache[cache_key]

    path = _weather_csv_path(state_key, city_key)
    if not os.path.exists(path):
        logger.warning(f"Weather dataset not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    _weather_df_cache[cache_key] = df
    logger.info(f"✅ Loaded {len(df):,} weather records for {city_key}")
    return df


def get_weather_for_hour(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> pd.DataFrame:
    """Return weather records for a given hour, averaged across days."""
    df = load_weather_data(state_key, city_key)
    if df.empty:
        return df

    hourly = df[df["hour"] == hour].copy()
    agg = (
        hourly.groupby(["area"])
        .agg(
            latitude          = ("latitude",          "mean"),
            longitude         = ("longitude",         "mean"),
            rainfall_mm_hr    = ("rainfall_mm_hr",    "mean"),
            visibility_km     = ("visibility_km",     "mean"),
            visibility_score  = ("visibility_score",  "mean"),
            wind_speed_kmh    = ("wind_speed_kmh",    "mean"),
            humidity_pct      = ("humidity_pct",      "mean"),
            temperature_c     = ("temperature_c",     "mean"),
            flood_risk        = ("flood_risk",        "mean"),
            waterlogging_risk = ("waterlogging_risk", "mean"),
            road_slipperiness = ("road_slipperiness", "mean"),
            weather_severity  = ("weather_severity",  "mean"),
        )
        .reset_index()
        .round(3)
    )
    # Dominant condition for this hour
    cond_mode = (
        hourly.groupby("area")["weather_condition"]
        .agg(lambda x: x.mode()[0] if not x.empty else "Clear")
        .rename("weather_condition")
    )
    agg = agg.merge(cond_mode, on="area", how="left")
    return agg


def get_point_weather(
    lat: float,
    lon: float,
    hour: int,
    radius_deg: float = 0.025,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """
    Return weather data for the area nearest to (lat, lon) at given hour.
    Falls back to a synthetic estimate when no nearby record exists.
    """
    df = get_weather_for_hour(hour, state_key, city_key)
    if df.empty:
        return _synthetic_weather(hour)

    dists = np.sqrt((df["latitude"] - lat) ** 2 + (df["longitude"] - lon) ** 2)
    idx   = int(dists.idxmin())

    if dists.iloc[idx] > radius_deg:
        return _synthetic_weather(hour)

    row = df.iloc[idx]
    return {
        "area":               row["area"],
        "weather_condition":  row["weather_condition"],
        "rainfall_mm_hr":     round(float(row["rainfall_mm_hr"]), 2),
        "visibility_km":      round(float(row["visibility_km"]), 1),
        "visibility_score":   round(float(row["visibility_score"]), 3),
        "wind_speed_kmh":     round(float(row["wind_speed_kmh"]), 1),
        "humidity_pct":       round(float(row["humidity_pct"]), 1),
        "temperature_c":      round(float(row["temperature_c"]), 1),
        "flood_risk":         round(float(row["flood_risk"]), 3),
        "waterlogging_risk":  round(float(row["waterlogging_risk"]), 3),
        "road_slipperiness":  round(float(row["road_slipperiness"]), 3),
        "weather_severity":   round(float(row["weather_severity"]), 3),
        "data_source":        "local_dataset",
        "hour":               hour,
    }


def _synthetic_weather(hour: int) -> dict:
    """Plausible weather snapshot when no dataset record is nearby."""
    is_night = hour >= 20 or hour < 6
    condition = "Clear" if np.random.random() > 0.35 else "Cloudy"
    return {
        "area":               "unknown",
        "weather_condition":  condition,
        "rainfall_mm_hr":     0.0,
        "visibility_km":      10.0 if condition == "Clear" else 7.5,
        "visibility_score":   0.95 if condition == "Clear" else 0.65,
        "wind_speed_kmh":     round(float(np.random.uniform(5, 15)), 1),
        "humidity_pct":       round(float(np.random.uniform(50, 70)), 1),
        "temperature_c":      round(float(np.random.uniform(20, 28)), 1),
        "flood_risk":         0.05,
        "waterlogging_risk":  0.05,
        "road_slipperiness":  0.08,
        "weather_severity":   0.05,
        "data_source":        "synthetic_estimate",
        "hour":               hour,
    }


def get_weather_heatmap(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Return [{ lat, lon, severity, condition, flood_risk, rainfall }, ...] for map layer."""
    df = get_weather_for_hour(hour, state_key, city_key)
    if df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            "lat":               round(float(row["latitude"]), 6),
            "lon":               round(float(row["longitude"]), 6),
            "severity":          round(float(row["weather_severity"]), 3),
            "condition":         row["weather_condition"],
            "flood_risk":        round(float(row["flood_risk"]), 3),
            "rainfall":          round(float(row["rainfall_mm_hr"]), 2),
            "visibility_km":     round(float(row["visibility_km"]), 1),
            "wind_speed_kmh":    round(float(row["wind_speed_kmh"]), 1),
            "road_slipperiness": round(float(row["road_slipperiness"]), 3),
            "area":              row["area"],
        })
    return result


def get_weather_stats(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Aggregated weather statistics for analytics dashboard."""
    df = get_weather_for_hour(hour, state_key, city_key)
    if df.empty:
        return {}

    flood_prone = df[df["flood_risk"] > 0.5][["area", "flood_risk", "waterlogging_risk"]].nlargest(5, "flood_risk").to_dict("records")
    low_vis     = df[df["visibility_km"] < 3.0][["area", "visibility_km"]].nsmallest(5, "visibility_km").to_dict("records")

    return {
        "avg_rainfall":       round(float(df["rainfall_mm_hr"].mean()), 2),
        "avg_visibility_km":  round(float(df["visibility_km"].mean()), 1),
        "avg_wind_kmh":       round(float(df["wind_speed_kmh"].mean()), 1),
        "avg_flood_risk":     round(float(df["flood_risk"].mean()), 3),
        "avg_severity":       round(float(df["weather_severity"].mean()), 3),
        "flood_prone_areas":  flood_prone,
        "low_visibility_areas": low_vis,
        "condition_distribution": df["weather_condition"].value_counts().to_dict(),
        "total_areas":        len(df),
        "hour":               hour,
    }


def get_weather_daily_trend(
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Average weather metrics by hour — for daily trend chart."""
    df = load_weather_data(state_key, city_key)
    if df.empty:
        return []
    trend = (
        df.groupby("hour")
        .agg(
            avg_rainfall    = ("rainfall_mm_hr",   "mean"),
            avg_visibility  = ("visibility_km",    "mean"),
            avg_flood_risk  = ("flood_risk",       "mean"),
            avg_severity    = ("weather_severity", "mean"),
            avg_wind        = ("wind_speed_kmh",   "mean"),
        )
        .reset_index()
        .round(3)
    )
    return trend.to_dict("records")


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE OPERATIONS (local fallback on every method)
# ═══════════════════════════════════════════════════════════════════════════════

def submit_weather_report(report: dict) -> dict:
    """Store a community or sensor weather report."""
    entry = {
        "id":              len(_weather_reports) + 1,
        "latitude":        report.get("latitude"),
        "longitude":       report.get("longitude"),
        "weather_type":    report.get("weather_type", "Clear"),
        "rainfall":        report.get("rainfall", 0.0),
        "visibility":      report.get("visibility", 10.0),
        "flood_risk":      report.get("flood_risk", 0.0),
        "wind_speed":      report.get("wind_speed", 10.0),
        "humidity":        report.get("humidity", 60.0),
        "temperature":     report.get("temperature", 25.0),
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }

    if _supabase_ready and _supabase:
        try:
            _supabase.table("weather_reports").insert(entry).execute()
            entry["source"] = "supabase"
            return entry
        except Exception as e:
            logger.warning(f"Supabase insert failed: {e}")

    _weather_reports.append(entry)
    entry["source"] = "local"
    return entry


def submit_road_weather_alert(alert: dict) -> dict:
    """Store a road-specific weather alert."""
    entry = {
        "id":          len(_road_weather_alerts) + 1,
        "road_name":   alert.get("road_name", "Unknown"),
        "alert_type":  alert.get("alert_type", "weather"),
        "severity":    alert.get("severity", 5),
        "description": alert.get("description", ""),
        "created_at":  datetime.now(timezone.utc).isoformat(),
    }

    if _supabase_ready and _supabase:
        try:
            _supabase.table("road_weather_alerts").insert(entry).execute()
            entry["source"] = "supabase"
            return entry
        except Exception as e:
            logger.warning(f"Supabase insert failed: {e}")

    _road_weather_alerts.append(entry)
    entry["source"] = "local"
    return entry


def get_weather_reports(limit: int = 100) -> List[dict]:
    """Fetch recent weather reports."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("weather_reports")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Supabase fetch failed: {e}")
    return list(reversed(_weather_reports))[-limit:]


def get_road_weather_alerts(limit: int = 50) -> List[dict]:
    """Fetch recent road-specific weather alerts."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("road_weather_alerts")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Supabase fetch failed: {e}")
    return list(reversed(_road_weather_alerts))[-limit:]


def get_supabase_status() -> dict:
    return {
        "connected": _supabase_ready,
        "mode":      "realtime" if _supabase_ready else "local_fallback",
    }
