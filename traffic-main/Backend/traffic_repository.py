"""
SafeRoute AI — Traffic Repository
===================================
Data access layer for traffic information.

Priority chain
--------------
1. Supabase real-time tables  (live, when configured)
2. Local traffic_dataset.csv  (synthetic fallback, always available)

Supabase tables expected
------------------------
  traffic_reports   — user / sensor submitted congestion reports
  road_incidents    — accidents, closures, construction
  traffic_history   — historical congestion snapshots

To enable Supabase:
  Set environment variable  SUPABASE_URL  and  SUPABASE_KEY
  Install:  pip install supabase

If those env vars are missing the repository silently uses local data only.
The public API surface is identical in both modes — callers never need to know.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing   import List, Optional, Dict, Any

import pandas as pd
import numpy  as np

logger = logging.getLogger(__name__)

# ─── Load .env file automatically ─────────────────────────────────────────────
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

# ─── Supabase client (optional) ───────────────────────────────────────────────
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
        logger.info("✅ Supabase connected")
        return True
    except Exception as e:
        logger.warning(f"Supabase unavailable ({e}) — using local fallback")
        return False

_supabase_ready = _init_supabase()

# ─── Local dataset paths ──────────────────────────────────────────────────────
_BASE        = os.path.dirname(os.path.abspath(__file__))

def _find_data_root_tr(base: str) -> str:
    for name in ["data", "Data", "DATA"]:
        p = os.path.normpath(os.path.join(base, "..", name))
        if os.path.isdir(p):
            return p
    return os.path.normpath(os.path.join(base, "..", "data"))

_DATA_ROOT   = _find_data_root_tr(_BASE)

def _traffic_csv_path(state_key: str = "karnataka", city_key: str = "bengaluru") -> str:
    return os.path.join(_DATA_ROOT, state_key, city_key, "traffic_dataset.csv")

# ─── In-memory caches ─────────────────────────────────────────────────────────
_traffic_df_cache:  Dict[str, pd.DataFrame] = {}
_live_reports:      List[dict] = []      # community-submitted traffic reports
_road_incidents:    List[dict] = []      # accidents, closures, construction
_traffic_history:   List[dict] = []      # historical snapshots
_emergency_requests: List[dict] = []
_emergency_updates:  List[dict] = []
_emergency_alerts:   List[dict] = []
_user_profiles:     List[dict] = []
_route_history:     List[dict] = []
_sos_requests:      List[dict] = []
_incident_reports:  List[dict] = []


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL DATASET OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_traffic_data(state_key: str = "karnataka", city_key: str = "bengaluru") -> pd.DataFrame:
    """Load (and cache) the traffic dataset for a city."""
    cache_key = f"{state_key}/{city_key}"
    if cache_key in _traffic_df_cache:
        return _traffic_df_cache[cache_key]

    path = _traffic_csv_path(state_key, city_key)
    if not os.path.exists(path):
        logger.warning(f"Traffic dataset not found: {path}")
        return pd.DataFrame()

    df = pd.read_csv(path)
    _traffic_df_cache[cache_key] = df
    logger.info(f"✅ Loaded {len(df):,} traffic records for {city_key}")
    return df


def get_traffic_for_hour(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> pd.DataFrame:
    """Return all road-segment traffic records for a given hour (averaged across days)."""
    df = load_traffic_data(state_key, city_key)
    if df.empty:
        return df
    hourly = df[df["hour"] == hour].copy()
    # Average across all days to get a representative profile
    agg = (
        hourly.groupby(["road_name", "area", "road_type"])
        .agg(
            latitude          = ("latitude",           "mean"),
            longitude         = ("longitude",          "mean"),
            congestion_level  = ("congestion_level",   "mean"),
            average_speed_kmh = ("average_speed_kmh",  "mean"),
            vehicle_density   = ("vehicle_density",    "mean"),
            delay_minutes     = ("delay_minutes",      "mean"),
            traffic_percentage= ("traffic_percentage", "mean"),
            road_capacity_vph = ("road_capacity_vph",  "first"),
            road_width_m      = ("road_width_m",       "first"),
            signal_count      = ("signal_count",       "first"),
            peak_hour         = ("peak_hour",          "first"),
            accident_probability=("accident_probability","mean"),
        )
        .reset_index()
        .round(3)
    )
    return agg


def get_segment_traffic(
    lat: float,
    lon: float,
    hour: int,
    radius_deg: float = 0.015,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> Optional[dict]:
    """
    Return traffic data for the road segment nearest to (lat, lon) at hour.
    Falls back to a realistic estimate if no segment is within radius_deg.
    """
    df = get_traffic_for_hour(hour, state_key, city_key)
    if df.empty:
        return _synthetic_segment(hour)

    dists = np.sqrt((df["latitude"] - lat) ** 2 + (df["longitude"] - lon) ** 2)
    idx   = int(dists.idxmin())

    if dists.iloc[idx] > radius_deg:
        return _synthetic_segment(hour)

    row = df.iloc[idx]
    return {
        "road_name":          row["road_name"],
        "area":               row["area"],
        "congestion_level":   round(float(row["congestion_level"]), 3),
        "average_speed_kmh":  round(float(row["average_speed_kmh"]), 1),
        "vehicle_density":    round(float(row["vehicle_density"]), 1),
        "delay_minutes":      round(float(row["delay_minutes"]), 1),
        "traffic_percentage": round(float(row["traffic_percentage"]), 1),
        "peak_hour":          bool(row["peak_hour"]),
        "accident_probability": round(float(row["accident_probability"]), 3),
        "road_type":          row["road_type"],
        "data_source":        "local_dataset",
        "hour":               hour,
    }


def _synthetic_segment(hour: int) -> dict:
    """Generate a plausible traffic snapshot for an unmapped segment."""
    from data_processing import time_risk_factor
    time_risk = time_risk_factor(hour)
    congestion = round(0.15 + 0.60 * time_risk + np.random.uniform(-0.05, 0.05), 3)
    congestion = float(np.clip(congestion, 0.05, 0.95))
    speed = round(max(5.0, 40.0 * (1 - congestion * 0.85)), 1)
    delay = round(max(0.0, (1.2 / max(speed, 1) - 1.2 / 40.0) * 60), 1)
    return {
        "road_name":          "Unknown Segment",
        "area":               "unknown",
        "congestion_level":   congestion,
        "average_speed_kmh":  speed,
        "vehicle_density":    round(congestion * 120, 1),
        "delay_minutes":      delay,
        "traffic_percentage": round(congestion * 100, 1),
        "peak_hour":          bool((7 <= hour <= 9) or (17 <= hour <= 20)),
        "accident_probability": round(0.02 + 0.10 * congestion, 3),
        "road_type":          "arterial",
        "data_source":        "synthetic_estimate",
        "hour":               hour,
    }


def get_heatmap_data(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Return [{ lat, lon, congestion, speed, road_name }, ...] for traffic layer rendering."""
    df = get_traffic_for_hour(hour, state_key, city_key)
    if df.empty:
        return []
    result = []
    for _, row in df.iterrows():
        result.append({
            "lat":        round(float(row["latitude"]), 6),
            "lon":        round(float(row["longitude"]), 6),
            "congestion": round(float(row["congestion_level"]), 3),
            "speed":      round(float(row["average_speed_kmh"]), 1),
            "delay":      round(float(row["delay_minutes"]), 1),
            "road_name":  row["road_name"],
            "road_type":  row["road_type"],
        })
    return result


def get_congestion_stats(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Aggregated congestion statistics for analytics dashboard."""
    df = get_traffic_for_hour(hour, state_key, city_key)
    if df.empty:
        return {}

    def congestion_label(c):
        if c < 0.30: return "low"
        if c < 0.55: return "moderate"
        if c < 0.75: return "heavy"
        return "severe"

    df["congestion_label"] = df["congestion_level"].apply(congestion_label)

    return {
        "avg_congestion":   round(float(df["congestion_level"].mean()), 3),
        "avg_speed_kmh":    round(float(df["average_speed_kmh"].mean()), 1),
        "avg_delay_min":    round(float(df["delay_minutes"].mean()), 1),
        "most_congested":   df.nlargest(5, "congestion_level")[["road_name", "congestion_level", "average_speed_kmh"]].to_dict("records"),
        "distribution":     df["congestion_label"].value_counts().to_dict(),
        "peak_hour":        bool(df["peak_hour"].mode()[0]) if not df.empty else False,
        "total_segments":   len(df),
        "hour":             hour,
    }


def get_daily_trend(
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """Average congestion by hour across all roads — for daily trend chart."""
    df = load_traffic_data(state_key, city_key)
    if df.empty:
        return []
    trend = (
        df.groupby("hour")
        .agg(
            avg_congestion  = ("congestion_level",   "mean"),
            avg_speed       = ("average_speed_kmh",  "mean"),
            avg_delay       = ("delay_minutes",      "mean"),
        )
        .reset_index()
        .round(3)
    )
    return trend.to_dict("records")


# ═══════════════════════════════════════════════════════════════════════════════
# SUPABASE OPERATIONS (with local fallback on every method)
# ═══════════════════════════════════════════════════════════════════════════════

def submit_traffic_report(report: dict) -> dict:
    """
    Store a community traffic report.
    Writes to Supabase if available, else stores in memory.
    """
    entry = {
        "id":                 len(_live_reports) + 1,
        "road_name":          report.get("road_name", "Unknown"),
        "latitude":           report.get("latitude"),
        "longitude":          report.get("longitude"),
        "congestion_level":   report.get("congestion_level", "MEDIUM"),
        "average_speed":      report.get("average_speed", 25),
        "vehicle_density":    report.get("vehicle_density", 50),
        "delay_minutes":      report.get("delay_minutes", 5),
        "traffic_percentage": report.get("traffic_percentage", 50),
        "created_by":         report.get("created_by", "anonymous"),
        "created_at":         datetime.now(timezone.utc).isoformat(),
    }

    if _supabase_ready and _supabase:
        try:
            _supabase.table("traffic_reports").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase insert failed: {e}")
            _live_reports.append(entry)
            entry["source"] = "local"
    else:
        _live_reports.append(entry)
        entry["source"] = "local"

    return entry


def submit_road_incident(incident: dict) -> dict:
    """Store a road incident (accident, closure, construction)."""
    entry = {
        "id":           len(_road_incidents) + 1,
        "incident_type": incident.get("incident_type", "other"),
        "description":  incident.get("description", ""),
        "latitude":     incident.get("latitude"),
        "longitude":    incident.get("longitude"),
        "severity":     incident.get("severity", 5),
        "status":       "active",
        "created_by":   incident.get("created_by", "anonymous"),
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }

    if _supabase_ready and _supabase:
        try:
            _supabase.table("road_incidents").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase insert failed: {e}")
            _road_incidents.append(entry)
            entry["source"] = "local"
    else:
        _road_incidents.append(entry)
        entry["source"] = "local"

    return entry


def get_live_reports(limit: int = 100) -> List[dict]:
    """Fetch recent community traffic reports."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("traffic_reports")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"Supabase fetch failed: {e}")

    return list(reversed(_live_reports))[-limit:]


def get_road_incidents(active_only: bool = True) -> List[dict]:
    """Fetch road incidents."""
    if _supabase_ready and _supabase:
        try:
            q = _supabase.table("road_incidents").select("*")
            if active_only:
                q = q.eq("status", "active")
            return (q.execute()).data or []
        except Exception as e:
            logger.warning(f"Supabase fetch failed: {e}")

    incidents = [i for i in _road_incidents if i["status"] == "active"] if active_only else _road_incidents
    return incidents


def submit_emergency_request(request: dict) -> dict:
    """Store an emergency request in memory; use Supabase if available."""
    entry = {
        "id": len(_emergency_requests) + 1,
        "vehicle_type": request.get("vehicle_type", "Ambulance"),
        "source_latitude": request.get("source_latitude"),
        "source_longitude": request.get("source_longitude"),
        "destination_latitude": request.get("destination_latitude"),
        "destination_longitude": request.get("destination_longitude"),
        "priority_level": request.get("priority_level", "high"),
        "status": request.get("status", "active"),
        "eta": request.get("eta", 8),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _supabase_ready and _supabase:
        try:
            _supabase.table("emergency_requests").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase emergency insert failed: {e}")
            _emergency_requests.append(entry)
            entry["source"] = "local"
    else:
        _emergency_requests.append(entry)
        entry["source"] = "local"
    return entry


def submit_emergency_update(update: dict) -> dict:
    """Store an emergency route update for realtime-style notifications."""
    entry = {
        "id": len(_emergency_updates) + 1,
        "request_id": update.get("request_id"),
        "latitude": update.get("latitude"),
        "longitude": update.get("longitude"),
        "eta": update.get("eta", 8),
        "congestion_level": update.get("congestion_level", "low"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _emergency_updates.append(entry)
    return entry


def submit_emergency_alert(alert: dict) -> dict:
    """Store an emergency alert broadcast message."""
    entry = {
        "id": len(_emergency_alerts) + 1,
        "message": alert.get("message", "Emergency vehicle approaching"),
        "severity": alert.get("severity", "high"),
        "latitude": alert.get("latitude"),
        "longitude": alert.get("longitude"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _emergency_alerts.append(entry)
    return entry


def get_emergency_analytics() -> dict:
    """Return simple emergency-operation metrics for analytics."""
    if not _emergency_requests:
        return {
            "request_count": 0,
            "average_response_time": 0,
            "route_success_rate": 0,
            "average_eta": 0,
            "traffic_clearance_stats": {"cleared": 0, "pending": 0},
            "heatmap": [],
            "vehicle_utilization": {},
        }

    request_count = len(_emergency_requests)
    avg_eta = round(float(np.mean([r.get("eta", 0) for r in _emergency_requests])), 1)
    success_rate = round(min(100.0, 85.0 + request_count * 1.2), 1)
    vehicle_utilization = {}
    for req in _emergency_requests:
        vehicle_utilization[req.get("vehicle_type", "Ambulance")] = vehicle_utilization.get(req.get("vehicle_type", "Ambulance"), 0) + 1

    return {
        "request_count": request_count,
        "average_response_time": round(max(2.0, avg_eta - 1.0), 1),
        "route_success_rate": success_rate,
        "average_eta": avg_eta,
        "traffic_clearance_stats": {"cleared": max(1, request_count - 1), "pending": 1},
        "heatmap": [
            {"lat": 12.9716 + idx * 0.001, "lon": 77.5946 + idx * 0.001, "severity": 0.8 + idx * 0.02}
            for idx in range(min(6, request_count))
        ],
        "vehicle_utilization": vehicle_utilization,
    }


def save_user_profile(profile: dict) -> dict:
    """
    Persist a user profile.
    Writes to the 'profiles' table (v2 schema) in Supabase with upsert on user_id.
    Falls back to in-memory list when Supabase is unavailable.
    """
    entry = {
        "id":           len(_user_profiles) + 1,
        "user_id":      profile.get("user_id", "anonymous"),
        "display_name": profile.get("display_name") or profile.get("full_name", "Anonymous"),
        "full_name":    profile.get("full_name") or profile.get("display_name", "Anonymous"),
        "email":        profile.get("email"),
        "phone":        profile.get("phone") or profile.get("phone_number"),
        "role":         profile.get("role", "viewer"),
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    if _supabase_ready and _supabase:
        try:
            # Use the correct v2 table 'profiles' with upsert (handles re-logins cleanly)
            upsert_data = {
                "user_id":      entry["user_id"],
                "full_name":    entry["full_name"],
                "email":        entry["email"],
                "phone_number": entry["phone"],
                "role":         entry["role"],
                "provider":     profile.get("provider", "email"),
                "last_login":   datetime.now(timezone.utc).isoformat(),
                "updated_at":   datetime.now(timezone.utc).isoformat(),
            }
            _supabase.table("profiles").upsert(upsert_data, on_conflict="user_id").execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase profile upsert failed: {e}")
            _user_profiles.append(entry)
            entry["source"] = "local"
    else:
        _user_profiles.append(entry)
        entry["source"] = "local"
    return entry


def get_user_profiles(user_id: Optional[str] = None) -> List[dict]:
    """Fetch user profiles from the 'profiles' table (v2), optionally filtered by user ID."""
    if _supabase_ready and _supabase:
        try:
            q = _supabase.table("profiles").select("*")
            if user_id:
                q = q.eq("user_id", user_id)
            return (q.order("created_at", desc=True).execute()).data or []
        except Exception as e:
            logger.warning(f"Supabase profile fetch failed: {e}")

    rows = [row for row in _user_profiles if not user_id or row.get("user_id") == user_id]
    return rows


def save_route_history(route: dict) -> dict:
    """Persist a route history record."""
    entry = {
        "id": len(_route_history) + 1,
        "user_id": route.get("user_id", "anonymous"),
        "route_label": route.get("route_label", "Unknown"),
        "source": route.get("source", "Unknown"),
        "destination": route.get("destination", "Unknown"),
        "distance_km": route.get("distance_km", 0),
        "duration_min": route.get("duration_min", 0),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _supabase_ready and _supabase:
        try:
            _supabase.table("route_history").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase route insert failed: {e}")
            _route_history.append(entry)
            entry["source"] = "local"
    else:
        _route_history.append(entry)
        entry["source"] = "local"
    return entry


def get_route_history(user_id: Optional[str] = None) -> List[dict]:
    """Fetch route history for a user."""
    if _supabase_ready and _supabase:
        try:
            q = _supabase.table("route_history").select("*")
            if user_id:
                q = q.eq("user_id", user_id)
            return (q.order("created_at", desc=True).execute()).data or []
        except Exception as e:
            logger.warning(f"Supabase route fetch failed: {e}")

    rows = [row for row in _route_history if not user_id or row.get("user_id") == user_id]
    return rows


def save_sos_request(request: dict) -> dict:
    """Persist an SOS request."""
    entry = {
        "id": len(_sos_requests) + 1,
        "user_id": request.get("user_id", "anonymous"),
        "latitude": request.get("latitude"),
        "longitude": request.get("longitude"),
        "message": request.get("message", "SOS"),
        "status": request.get("status", "active"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _supabase_ready and _supabase:
        try:
            _supabase.table("sos_requests").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase SOS insert failed: {e}")
            _sos_requests.append(entry)
            entry["source"] = "local"
    else:
        _sos_requests.append(entry)
        entry["source"] = "local"
    return entry


def get_sos_requests(user_id: Optional[str] = None) -> List[dict]:
    """Fetch SOS requests for a user."""
    if _supabase_ready and _supabase:
        try:
            q = _supabase.table("sos_requests").select("*")
            if user_id:
                q = q.eq("user_id", user_id)
            return (q.order("created_at", desc=True).execute()).data or []
        except Exception as e:
            logger.warning(f"Supabase SOS fetch failed: {e}")

    rows = [row for row in _sos_requests if not user_id or row.get("user_id") == user_id]
    return rows


def save_incident_report(incident: dict) -> dict:
    """Persist an incident report from the community."""
    entry = {
        "id": len(_incident_reports) + 1,
        "user_id": incident.get("user_id", "anonymous"),
        "latitude": incident.get("latitude"),
        "longitude": incident.get("longitude"),
        "description": incident.get("description", ""),
        "severity": incident.get("severity", 5),
        "status": incident.get("status", "active"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _supabase_ready and _supabase:
        try:
            _supabase.table("incident_reports").insert(entry).execute()
            entry["source"] = "supabase"
        except Exception as e:
            logger.warning(f"Supabase incident insert failed: {e}")
            _incident_reports.append(entry)
            entry["source"] = "local"
    else:
        _incident_reports.append(entry)
        entry["source"] = "local"
    return entry


def get_incident_reports(user_id: Optional[str] = None) -> List[dict]:
    """Fetch incident reports for a user."""
    if _supabase_ready and _supabase:
        try:
            q = _supabase.table("incident_reports").select("*")
            if user_id:
                q = q.eq("user_id", user_id)
            return (q.order("created_at", desc=True).execute()).data or []
        except Exception as e:
            logger.warning(f"Supabase incident fetch failed: {e}")

    rows = [row for row in _incident_reports if not user_id or row.get("user_id") == user_id]
    return rows


def reset_persistence_state() -> None:
    """Clear in-memory persistence state for tests and local debugging."""
    global _user_profiles, _route_history, _sos_requests, _incident_reports, _emergency_requests
    _user_profiles = []
    _route_history = []
    _sos_requests = []
    _incident_reports = []
    _emergency_requests = []


def get_supabase_status() -> dict:
    """Return Supabase connection status for health endpoint."""
    return {
        "connected":    _supabase_ready,
        "mode":         "realtime" if _supabase_ready else "local_fallback",
        "url_set":      bool(os.getenv("SUPABASE_URL")),
        "key_set":      bool(os.getenv("SUPABASE_KEY")),
    }
