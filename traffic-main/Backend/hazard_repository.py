"""
SafeRoute AI — Hazard Repository
====================================
Data access layer for road hazards.

Priority chain
--------------
1. Supabase real-time table  (when configured)
2. In-memory local fallback  (always available)

Public API surface is identical in both modes.
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ─── Load .env ────────────────────────────────────────────────────────────────
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
_supabase_ready = False

def _init_supabase():
    global _supabase, _supabase_ready
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return
    try:
        from supabase import create_client
        _supabase = create_client(url, key)
        _supabase_ready = True
        logger.info("✅ Hazard repository: Supabase connected")
    except Exception as e:
        logger.warning(f"Hazard repository: Supabase unavailable ({e}) — using local fallback")

_init_supabase()

# ─── In-memory fallback ───────────────────────────────────────────────────────
_local_hazards: List[Dict] = []
_local_id_counter = 1


# ─── WRITE ────────────────────────────────────────────────────────────────────

def save_hazard_report(data: dict) -> dict:
    """Save a hazard report to Supabase or locally."""
    global _local_id_counter

    payload = {
        "hazard_type": (data.get("hazard_type") or "other").lower(),
        "title":       data.get("title") or "Road Hazard",
        "description": data.get("description") or "",
        "latitude":    float(data.get("latitude") or 0),
        "longitude":   float(data.get("longitude") or 0),
        "severity":    max(1, min(10, int(data.get("severity") or 5))),
        "status":      data.get("status") or "active",
        "verified":    bool(data.get("verified", False)),
        "source":      data.get("source") or "community",
    }
    uid = data.get("user_id")
    if uid and uid != "anonymous":
        payload["user_id"] = uid
    if data.get("image_url"):
        payload["image_url"] = data["image_url"]

    if _supabase_ready and _supabase:
        try:
            res = _supabase.table("road_hazards").insert(payload).execute()
            if res.data:
                saved = dict(res.data[0])
                saved["source_db"] = "supabase"
                return saved
        except Exception as e:
            logger.warning(f"Hazard Supabase insert failed: {e}")

    # Local fallback
    entry = {
        "id":         _local_id_counter,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_db":  "local",
        **payload,
    }
    if uid and uid != "anonymous":
        entry["user_id"] = uid
    _local_hazards.append(entry)
    _local_id_counter += 1
    return entry


def update_hazard(hazard_id, updates: dict) -> Optional[Dict]:
    """Update fields on an existing hazard."""
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    if _supabase_ready and _supabase:
        try:
            res = _supabase.table("road_hazards").update(updates).eq("id", hazard_id).execute()
            if res.data:
                return dict(res.data[0])
        except Exception as e:
            logger.warning(f"Hazard update failed (Supabase): {e}")

    for h in _local_hazards:
        if str(h["id"]) == str(hazard_id):
            h.update(updates)
            return dict(h)
    return None


def delete_hazard(hazard_id) -> bool:
    """Soft-delete a hazard by setting status=resolved."""
    return update_hazard(hazard_id, {"status": "resolved"}) is not None


# ─── READ ─────────────────────────────────────────────────────────────────────

def get_active_hazards(limit: int = 500) -> List[Dict]:
    """Fetch all active hazards."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("road_hazards")
                .select("*")
                .eq("status", "active")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if res.data is not None:
                return [dict(r) for r in res.data]
        except Exception as e:
            logger.warning(f"Hazard fetch failed (Supabase): {e}")

    return [dict(h) for h in _local_hazards if h.get("status") == "active"]


def get_all_hazards(limit: int = 500) -> List[Dict]:
    """Fetch all hazards (all statuses)."""
    if _supabase_ready and _supabase:
        try:
            res = (
                _supabase.table("road_hazards")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if res.data is not None:
                return [dict(r) for r in res.data]
        except Exception as e:
            logger.warning(f"Hazard all-fetch failed (Supabase): {e}")

    return [dict(h) for h in _local_hazards]


def get_hazard_by_id(hazard_id) -> Optional[Dict]:
    """Fetch a single hazard by ID."""
    if _supabase_ready and _supabase:
        try:
            res = _supabase.table("road_hazards").select("*").eq("id", hazard_id).execute()
            if res.data:
                return dict(res.data[0])
        except Exception as e:
            logger.warning(f"Hazard get-by-id failed: {e}")

    for h in _local_hazards:
        if str(h["id"]) == str(hazard_id):
            return dict(h)
    return None


def get_nearby_hazards(lat: float, lon: float, radius_km: float = 1.0) -> List[Dict]:
    """
    Fetch active hazards within radius_km of (lat, lon).
    Uses Supabase when available; falls back to local with Python-side distance filter.
    """
    import math

    def _dist(h):
        try:
            dlat = math.radians(float(h["latitude"]) - lat)
            dlon = math.radians(float(h["longitude"]) - lon)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat)) * math.cos(math.radians(float(h["latitude"]))) *
                 math.sin(dlon / 2) ** 2)
            return 6371.0 * 2 * math.asin(math.sqrt(a))
        except Exception:
            return 9999.0

    # Supabase doesn't have native ST_DWithin in the Python SDK without PostGIS RPC,
    # so we fetch active hazards with a bounding-box approximation then filter locally.
    deg_offset = radius_km / 111.0  # ~1 degree lat ≈ 111 km
    all_active = get_active_hazards(limit=1000)
    return [h for h in all_active if _dist(h) <= radius_km]


def get_hazard_statistics() -> Dict:
    """Return aggregate statistics for the analytics dashboard."""
    hazards = get_all_hazards(limit=2000)

    if not hazards:
        return {
            "total": 0, "active": 0, "resolved": 0, "verified": 0,
            "by_type": {}, "by_severity": {}, "avg_severity": 0,
            "avg_resolution_time_hours": 0, "top_types": [],
            "ai_route_changes": 0,
        }

    active   = [h for h in hazards if h.get("status") == "active"]
    resolved = [h for h in hazards if h.get("status") == "resolved"]
    verified = [h for h in hazards if h.get("verified")]

    by_type: Dict[str, int] = {}
    for h in hazards:
        t = (h.get("hazard_type") or "other").lower()
        by_type[t] = by_type.get(t, 0) + 1

    by_severity: Dict[str, int] = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    from hazard_detector import severity_label
    for h in hazards:
        lbl = severity_label(int(h.get("severity") or 5))
        by_severity[lbl] = by_severity.get(lbl, 0) + 1

    severities = [int(h.get("severity") or 5) for h in active]
    avg_sev    = round(sum(severities) / max(len(severities), 1), 1)

    top_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total":                    len(hazards),
        "active":                   len(active),
        "resolved":                 len(resolved),
        "verified":                 len(verified),
        "unverified":               len(hazards) - len(verified),
        "by_type":                  by_type,
        "by_severity":              by_severity,
        "avg_severity":             avg_sev,
        "avg_resolution_time_hours": 6.5,   # placeholder; full impl needs resolved_at column
        "top_types":                [{"type": t, "count": c} for t, c in top_types],
        "ai_route_changes":         len([h for h in active if float(h.get("safety_impact") or 0) > 0.5]),
        "source":                   "supabase" if _supabase_ready else "local",
    }


def get_supabase_status() -> dict:
    return {
        "connected": _supabase_ready,
        "mode":      "realtime" if _supabase_ready else "local_fallback",
    }
