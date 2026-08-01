"""
SafeRoute AI — Crowd Density Service
=======================================
Business logic for crowd-aware routing.

Responsibilities
----------------
• Predict crowd density along a route
• Compute crowd score for AI route ranking
• Enrich route dicts with crowd data
• Generate live crowd alerts
• Implement final 35/25/15/15/10 scoring formula

This module is stateless — all data comes from crowd_repository.
It does NOT modify route_engine, safety_score, risk_model,
traffic_service, or weather_service.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional

import crowd_repository as cr


# ─── Crowd level metadata ─────────────────────────────────────────────────────
CROWD_META = {
    "Low":      {"emoji": "🟢", "color": "#3fb950", "label": "Low",      "safe": True},
    "Moderate": {"emoji": "🟡", "color": "#d29922", "label": "Moderate", "safe": True},
    "High":     {"emoji": "🟠", "color": "#f85149", "label": "High",     "safe": False},
    "Extreme":  {"emoji": "🔴", "color": "#ff0000", "label": "Extreme",  "safe": False},
}

def _crowd_meta(level: str) -> dict:
    return CROWD_META.get(level, CROWD_META["Moderate"])


# ─── Crowd score (0–100, higher = less crowded = better for routing) ─────────

def compute_crowd_score(crowd_point: dict) -> float:
    """
    Calculate a 0–100 crowd score for routing.

    Higher score = less crowded = better for route selection.

    Components
    ----------
    • crowd_score (density)  — 60% weight (inverted)
    • overcrowd_risk         — 25% weight (inverted)
    • isolation_risk         — 15% weight (inverted — isolated is also unsafe)
    """
    density     = float(crowd_point.get("crowd_score",     0.35))
    overcrowd   = float(crowd_point.get("overcrowd_risk",  0.3))
    isolation   = float(crowd_point.get("isolation_risk",  0.2))

    # Safety composite: both extremes (overcrowded AND isolated) are risky
    raw_risk = (
        0.60 * density    +
        0.25 * overcrowd  +
        0.15 * isolation
    )
    return round(float(np.clip((1.0 - raw_risk) * 100, 0.0, 100.0)), 2)


# ─── Route crowd analysis ─────────────────────────────────────────────────────

def analyse_route_crowd(
    coordinates: List[list],
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """
    Analyse crowd density along a route's waypoints.

    Returns a full crowd summary dict for the route.
    """
    if not coordinates or len(coordinates) < 2:
        return _empty_crowd_result(hour)

    sample = coordinates[::2] if len(coordinates) > 6 else coordinates

    point_results = []
    for pt in sample:
        lat, lon = float(pt[0]), float(pt[1])
        pc = cr.get_point_crowd(lat, lon, hour, state_key=state_key, city_key=city_key)
        if pc:
            point_results.append(pc)

    if not point_results:
        return _empty_crowd_result(hour)

    # Aggregate
    avg_score    = float(np.mean([p["crowd_score"]      for p in point_results]))
    avg_people   = int(np.mean([p["estimated_people"]   for p in point_results]))
    avg_iso      = float(np.mean([p["isolation_risk"]   for p in point_results]))
    avg_over     = float(np.mean([p["overcrowd_risk"]   for p in point_results]))
    avg_util     = float(np.mean([p["utilisation_pct"]  for p in point_results]))

    # Worst crowd level along the route
    level_order  = ["Extreme", "High", "Moderate", "Low"]
    levels_seen  = [p["crowd_level"] for p in point_results]
    worst_level  = next((l for l in level_order if l in levels_seen), "Low")

    # Overall crowd score for routing (higher = better)
    worst_point  = max(point_results, key=lambda p: p["crowd_score"])
    crowd_score  = compute_crowd_score(worst_point)

    # Peak people estimate
    max_people   = max(p["estimated_people"] for p in point_results)
    meta         = _crowd_meta(worst_level)

    return {
        "crowd_level":       worst_level,
        "crowd_label":       meta["label"],
        "crowd_emoji":       meta["emoji"],
        "crowd_color":       meta["color"],
        "crowd_safe":        meta["safe"],
        "avg_crowd_score":   round(avg_score, 3),
        "crowd_score":       crowd_score,        # routing score 0–100 (higher = better)
        "estimated_people":  avg_people,
        "max_people":        max_people,
        "utilisation_pct":   round(avg_util, 1),
        "isolation_risk":    round(avg_iso, 3),
        "overcrowd_risk":    round(avg_over, 3),
        "point_count":       len(point_results),
    }


def _empty_crowd_result(hour: int) -> dict:
    """Fallback when no crowd data is available."""
    is_peak = (7 <= hour <= 9) or (17 <= hour <= 21)
    score   = 0.55 if is_peak else 0.30
    level   = "Moderate" if is_peak else "Low"
    meta    = _crowd_meta(level)
    return {
        "crowd_level":       level,
        "crowd_label":       meta["label"],
        "crowd_emoji":       meta["emoji"],
        "crowd_color":       meta["color"],
        "crowd_safe":        meta["safe"],
        "avg_crowd_score":   score,
        "crowd_score":       round((1 - score) * 100, 2),
        "estimated_people":  int(score * 1000),
        "max_people":        int(score * 1500),
        "utilisation_pct":   round(score * 100, 1),
        "isolation_risk":    0.15,
        "overcrowd_risk":    score * 0.6,
        "point_count":       0,
    }


# ─── Final AI Route Score (35/25/15/15/10 formula) ───────────────────────────

def compute_final_route_score(
    safety_score:  float,      # 0–100
    duration_min:  float,      # minutes
    traffic_score: float,      # 0–100
    weather_score: float,      # 0–100
    crowd_score:   float,      # 0–100
    max_duration:  float = 60,
) -> float:
    """
    Final weighted AI score:
      35% Safety Score
      25% Travel Time Score
      15% Traffic Score
      15% Weather Score
      10% Crowd Density Score
    """
    time_score = max(0.0, 100.0 - (duration_min / max(max_duration, 1)) * 100)
    final = (
        0.35 * safety_score  +
        0.25 * time_score    +
        0.15 * traffic_score +
        0.15 * weather_score +
        0.10 * crowd_score
    )
    return round(float(np.clip(final, 0.0, 100.0)), 2)


# ─── Enrich routes with crowd data ───────────────────────────────────────────

def enrich_routes_with_crowd(
    routes: List[dict],
    hour:   int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """
    Add crowd data to each route dict.
    Upgrades ai_score to 35/25/15/15/10 formula.
    Existing keys are never removed.
    """
    max_duration = max(
        (r.get("eta_with_traffic", r.get("duration_min", 30)) for r in routes),
        default=30
    )

    for route in routes:
        coords = route.get("coordinates") or route.get("geometry") or []
        crowd  = analyse_route_crowd(coords, hour, state_key, city_key)

        # Inject crowd fields
        route["crowd_level"]       = crowd["crowd_level"]
        route["crowd_label"]       = crowd["crowd_label"]
        route["crowd_emoji"]       = crowd["crowd_emoji"]
        route["crowd_color"]       = crowd["crowd_color"]
        route["crowd_safe"]        = crowd["crowd_safe"]
        route["estimated_people"]  = crowd["estimated_people"]
        route["max_people"]        = crowd["max_people"]
        route["crowd_score"]       = crowd["crowd_score"]
        route["utilisation_pct"]   = crowd["utilisation_pct"]
        route["isolation_risk"]    = crowd["isolation_risk"]
        route["overcrowd_risk"]    = crowd["overcrowd_risk"]

        # Final AI Score (35/25/15/15/10)
        route["ai_score"] = compute_final_route_score(
            safety_score  = float(route.get("safety_score",   50)),
            duration_min  = float(route.get("eta_with_traffic", route.get("duration_min", 15))),
            traffic_score = float(route.get("traffic_score",  70)),
            weather_score = float(route.get("weather_score",  80)),
            crowd_score   = crowd["crowd_score"],
            max_duration  = max_duration + 10,
        )

    # Re-assign AI Recommended badge
    if routes:
        best = max(routes, key=lambda r: r.get("ai_score", 0))
        for r in routes:
            if r is best:
                r["badge"] = "⭐ AI Recommended" if r.get("type") == "Safest" else "⭐ AI Recommended (Optimal)"
            elif not r.get("badge"):
                r["badge"] = ""

    return routes


# ─── Crowd alerts ─────────────────────────────────────────────────────────────

def generate_crowd_alerts(routes: List[dict]) -> List[dict]:
    """
    Scan routes for crowd-related hazards and generate user-facing alerts.
    Covers both extreme crowding AND dangerous isolation.
    """
    alerts = []
    is_night = False  # will be set if routes have hour info

    for route in routes:
        level    = route.get("crowd_level", "Low")
        people   = route.get("estimated_people", 0)
        iso_risk = route.get("isolation_risk", 0.0)

        if level == "Extreme":
            safer = next((r for r in routes if r is not route and
                         r.get("crowd_level") not in ("Extreme", "High")), None)
            alerts.append({
                "type":    "extreme_crowd",
                "level":   "danger",
                "route":   route["type"],
                "message": (
                    f"🔴 Extremely crowded ahead on {route['type']} Route "
                    f"({people:,} people). "
                    + (f"AI recommends {safer['type']} Route." if safer else "Proceed with caution.")
                ),
            })

        elif level == "High":
            alerts.append({
                "type":    "high_crowd",
                "level":   "warning",
                "route":   route["type"],
                "message": f"🟠 Heavy crowd detected on {route['type']} Route (~{people:,} people). AI suggests Balanced Route.",
            })

        elif iso_risk > 0.55:
            alerts.append({
                "type":    "isolation_warning",
                "level":   "warning",
                "route":   route["type"],
                "message": f"🚶 Isolated area detected on {route['type']} Route. Use caution during night hours.",
            })

    return alerts


# ─── Crowd heatmap for frontend ───────────────────────────────────────────────

def get_crowd_heatmap(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
    limit: int = 200,
) -> List[dict]:
    """Return crowd heatmap data for Leaflet rendering."""
    data = cr.get_crowd_heatmap(hour, state_key, city_key)
    return data[:limit]


def get_crowd_analytics(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Full crowd analytics payload for dashboard."""
    stats   = cr.get_crowd_stats(hour, state_key, city_key)
    trend   = cr.get_crowd_daily_trend(state_key, city_key)
    reports = cr.get_crowd_reports(limit=20)

    return {
        "crowd_stats":     stats,
        "daily_trend":     trend,
        "recent_reports":  reports,
        "supabase_status": cr.get_supabase_status(),
        "hour":            hour,
        "formula":         "35% Safety + 25% Time + 15% Traffic + 15% Weather + 10% Crowd",
    }
