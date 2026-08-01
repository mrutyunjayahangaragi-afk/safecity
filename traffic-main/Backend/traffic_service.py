"""
SafeRoute AI — Traffic Service
================================
Business logic for traffic analysis and route scoring.

Responsibilities
----------------
• Enrich a route's waypoints with traffic data
• Compute traffic score for a route (used in 50/30/20 formula)
• Generate live traffic alerts
• Provide congestion label and color for the frontend

This module is stateless — all data comes from traffic_repository.
It does NOT modify route_engine, safety_score, or risk_model.
"""

from __future__ import annotations

import numpy as np
from typing import List, Dict, Optional, Tuple

import traffic_repository as tr


# ─── Congestion thresholds ────────────────────────────────────────────────────
CONGESTION_LOW      = 0.30
CONGESTION_MODERATE = 0.55
CONGESTION_HEAVY    = 0.75

CONGESTION_LABELS = {
    "low":      {"label": "Low",      "color": "#3fb950", "emoji": "🟢"},
    "moderate": {"label": "Moderate", "color": "#d29922", "emoji": "🟡"},
    "heavy":    {"label": "Heavy",    "color": "#f85149", "emoji": "🟠"},
    "severe":   {"label": "Severe",   "color": "#ff0000", "emoji": "🔴"},
}


def _congestion_label(level: float) -> str:
    if level < CONGESTION_LOW:      return "low"
    if level < CONGESTION_MODERATE: return "moderate"
    if level < CONGESTION_HEAVY:    return "heavy"
    return "severe"


# ─── Route traffic analysis ───────────────────────────────────────────────────

def analyse_route_traffic(
    coordinates: List[list],
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """
    Analyse traffic conditions along a route's waypoints.

    Parameters
    ----------
    coordinates : [[lat, lon], ...]  — route geometry
    hour        : hour of travel (0–23)

    Returns
    -------
    {
        avg_congestion, avg_speed_kmh, total_delay_min,
        traffic_score (0–100, higher = better traffic),
        traffic_status, congestion_pct, peak_hour,
        segment_data: [{...}, ...]
    }
    """
    if not coordinates or len(coordinates) < 2:
        return _empty_traffic_result(hour)

    # Sample every 2nd waypoint to reduce computation
    sample = coordinates[::2] if len(coordinates) > 6 else coordinates

    segment_results = []
    for pt in sample:
        lat, lon = float(pt[0]), float(pt[1])
        seg = tr.get_segment_traffic(lat, lon, hour, state_key=state_key, city_key=city_key)
        if seg:
            segment_results.append(seg)

    if not segment_results:
        return _empty_traffic_result(hour)

    congestions = [s["congestion_level"] for s in segment_results]
    speeds      = [s["average_speed_kmh"] for s in segment_results]
    delays      = [s["delay_minutes"]     for s in segment_results]

    avg_cong  = float(np.mean(congestions))
    avg_speed = float(np.mean(speeds))
    total_del = float(np.sum(delays))

    # Traffic score: higher = better (inverse of congestion)
    traffic_score = round((1.0 - avg_cong) * 100, 1)

    label = _congestion_label(avg_cong)
    meta  = CONGESTION_LABELS[label]

    return {
        "avg_congestion":   round(avg_cong, 3),
        "avg_speed_kmh":    round(avg_speed, 1),
        "total_delay_min":  round(total_del, 1),
        "traffic_score":    traffic_score,
        "traffic_status":   label,
        "traffic_label":    meta["label"],
        "traffic_color":    meta["color"],
        "traffic_emoji":    meta["emoji"],
        "congestion_pct":   round(avg_cong * 100, 1),
        "peak_hour":        any(s.get("peak_hour") for s in segment_results),
        "segment_count":    len(segment_results),
        "segment_data":     segment_results[:5],   # cap payload size
    }


def _empty_traffic_result(hour: int) -> dict:
    """Fallback when no traffic data is available."""
    from data_processing import time_risk_factor
    time_risk  = time_risk_factor(hour)
    congestion = round(0.15 + 0.50 * time_risk, 3)
    speed      = round(max(5.0, 40.0 * (1 - congestion * 0.85)), 1)
    return {
        "avg_congestion":   congestion,
        "avg_speed_kmh":    speed,
        "total_delay_min":  round((1.0 / max(speed, 1) - 1.0 / 40.0) * 60 * 3, 1),
        "traffic_score":    round((1.0 - congestion) * 100, 1),
        "traffic_status":   _congestion_label(congestion),
        "traffic_label":    CONGESTION_LABELS[_congestion_label(congestion)]["label"],
        "traffic_color":    CONGESTION_LABELS[_congestion_label(congestion)]["color"],
        "traffic_emoji":    CONGESTION_LABELS[_congestion_label(congestion)]["emoji"],
        "congestion_pct":   round(congestion * 100, 1),
        "peak_hour":        bool((7 <= hour <= 9) or (17 <= hour <= 20)),
        "segment_count":    0,
        "segment_data":     [],
    }


# ─── Final AI Route Score (50/30/20 formula) ─────────────────────────────────

def compute_final_route_score(
    safety_score: float,      # 0–100  (higher = safer)
    duration_min: float,      # minutes (lower = better)
    traffic_score: float,     # 0–100  (higher = better)
    max_duration: float = 60, # used to normalise duration
) -> float:
    """
    Weighted final AI score as specified:
      50% Safety Score
      30% Travel Time Score  (normalised, lower duration → higher score)
      20% Traffic Score

    Returns a score 0–100.
    """
    time_score = max(0.0, 100.0 - (duration_min / max(max_duration, 1)) * 100)
    final = (
        0.50 * safety_score +
        0.30 * time_score   +
        0.20 * traffic_score
    )
    return round(float(np.clip(final, 0.0, 100.0)), 2)


def enrich_routes_with_traffic(
    routes: List[dict],
    hour:   int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """
    Add traffic data to each route dict returned by route_engine.find_route_comparison.

    Modifies routes in-place and returns the list.
    Existing keys are never removed.
    """
    max_duration = max((r.get("duration_min", 30) for r in routes), default=30)

    for route in routes:
        coords = route.get("coordinates") or route.get("geometry") or []
        traffic = analyse_route_traffic(coords, hour, state_key, city_key)

        # Inject traffic fields
        route["traffic_status"]   = traffic["traffic_status"]
        route["traffic_label"]    = traffic["traffic_label"]
        route["traffic_color"]    = traffic["traffic_color"]
        route["traffic_emoji"]    = traffic["traffic_emoji"]
        route["congestion_pct"]   = traffic["congestion_pct"]
        route["avg_speed_kmh"]    = traffic["avg_speed_kmh"]
        route["traffic_delay_min"]= traffic["total_delay_min"]
        route["peak_hour"]        = traffic["peak_hour"]
        route["traffic_score"]    = traffic["traffic_score"]

        # Adjust ETA by traffic delay
        base_dur = float(route.get("duration_min", 10))
        route["eta_with_traffic"] = round(base_dur + traffic["total_delay_min"], 1)

        # Final AI Score (50/30/20)
        route["ai_score"] = compute_final_route_score(
            safety_score  = float(route.get("safety_score", 50)),
            duration_min  = route["eta_with_traffic"],
            traffic_score = traffic["traffic_score"],
            max_duration  = max_duration + 10,
        )

    # Re-assign AI Recommended badge to route with highest ai_score
    if routes:
        best = max(routes, key=lambda r: r.get("ai_score", 0))
        for r in routes:
            if r is best and r.get("type") == "Safest":
                r["badge"] = "⭐ AI Recommended"
            elif r is best:
                r["badge"] = "⭐ AI Recommended (Traffic)"
            elif not r.get("badge"):
                r["badge"] = ""

    return routes


# ─── Live alert generation ────────────────────────────────────────────────────

def generate_traffic_alerts(routes: List[dict]) -> List[dict]:
    """
    Scan routes for heavy congestion and generate user-facing alerts.
    These are displayed as toast notifications in the frontend.
    """
    alerts = []

    for route in routes:
        status = route.get("traffic_status", "low")
        delay  = route.get("traffic_delay_min", 0)

        if status in ("heavy", "severe"):
            # Find alternative with better traffic
            alternatives = [
                r for r in routes
                if r is not route and r.get("traffic_status") not in ("heavy", "severe")
            ]
            if alternatives:
                best_alt = min(alternatives, key=lambda r: r.get("eta_with_traffic", 99))
                saved    = round(route.get("eta_with_traffic", 0) - best_alt.get("eta_with_traffic", 0), 1)
                if saved > 0:
                    alerts.append({
                        "type":    "congestion_warning",
                        "level":   "warning",
                        "route":   route["type"],
                        "message": (
                            f"🚦 Heavy traffic on {route['type']} Route. "
                            f"AI recommends {best_alt['type']} Route. "
                            f"Est. time saved: {saved} min."
                        ),
                        "time_saved_min": saved,
                        "recommended_route": best_alt["type"],
                    })

    return alerts


# ─── Traffic heatmap for frontend ────────────────────────────────────────────

def get_traffic_heatmap(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
    limit: int = 300,
) -> List[dict]:
    """Return traffic heatmap data for Leaflet rendering."""
    data = tr.get_heatmap_data(hour, state_key, city_key)
    return data[:limit]


def get_traffic_analytics(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Full analytics payload for the dashboard."""
    stats = tr.get_congestion_stats(hour, state_key, city_key)
    trend = tr.get_daily_trend(state_key, city_key)
    incidents = tr.get_road_incidents(active_only=True)

    return {
        "congestion_stats":  stats,
        "daily_trend":       trend,
        "active_incidents":  incidents,
        "supabase_status":   tr.get_supabase_status(),
        "hour":              hour,
    }
