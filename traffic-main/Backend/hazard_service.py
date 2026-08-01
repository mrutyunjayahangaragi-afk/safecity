"""
SafeRoute AI — Hazard Service
================================
Business logic for AI Road Hazard Detection and Avoidance.

Responsibilities
----------------
• Enrich hazard reports with AI confidence + impact scores
• Analyse hazards along a route and compute hazard score
• Generate live hazard alerts for the frontend
• Compute segment-level routing penalty
• Provide the new 5-factor final AI score (30/20/15/10/25)

This module is stateless — all data comes from hazard_repository.
It does NOT replace any existing logic in route_engine, safety_score,
traffic_service, weather_service, or crowd_service.
Only extends them.
"""

from __future__ import annotations

import math
from typing import List, Dict, Optional

import hazard_repository as hr
import hazard_detector   as hd


# ─── Public helpers ───────────────────────────────────────────────────────────

def report_hazard(data: dict) -> dict:
    """
    Process a new hazard report:
      1. Save to repository (Supabase or local)
      2. Fetch active hazards for confidence calculation
      3. Enrich with AI (confidence, impact, delay)
      4. Persist updated verified flag if changed
    """
    saved = hr.save_hazard_report(data)
    active = hr.get_active_hazards()
    enriched = hd.enrich_report_with_ai(saved, active)

    # Persist verified flag if AI promoted it
    if enriched.get("verified") and not saved.get("verified"):
        hr.update_hazard(enriched["id"], {"verified": True})

    return enriched


def get_active_hazards_enriched() -> List[dict]:
    """Return all active hazards with AI-computed fields."""
    hazards = hr.get_active_hazards()
    return [hd.enrich_report_with_ai(h, hazards) for h in hazards]


# ─── Route hazard analysis ────────────────────────────────────────────────────

def analyse_route_hazards(
    coordinates: List[list],
    active_hazards: Optional[List[dict]] = None,
) -> dict:
    """
    Analyse hazard exposure along a route.

    Returns a full hazard summary dict including:
      hazard_score (0-100, higher = safer),
      hazards_count, max_severity, max_impact,
      expected_delay_min, hazard_level, route_hazards
    """
    if not coordinates or len(coordinates) < 2:
        return _empty_hazard_result()

    if active_hazards is None:
        active_hazards = get_active_hazards_enriched()

    if not active_hazards:
        return _empty_hazard_result()

    route_hazards: List[dict] = []
    seen_ids = set()

    for point in coordinates:
        try:
            lat = float(point[0])
            lon = float(point[1])
        except (IndexError, TypeError, ValueError):
            continue

        for h in active_hazards:
            hid = h.get("id")
            if hid in seen_ids:
                continue
            h_lat = h.get("latitude")
            h_lon = h.get("longitude")
            if h_lat is None or h_lon is None:
                continue
            radius = h.get("proximity_radius_km") or hd.get_hazard_radius(
                (h.get("hazard_type") or "other").lower()
            )
            dist = hd.haversine(lat, lon, float(h_lat), float(h_lon))
            if dist <= radius:
                route_hazards.append(h)
                seen_ids.add(hid)

    if not route_hazards:
        return _empty_hazard_result()

    max_severity = max(int(h.get("severity") or 5) for h in route_hazards)
    max_impact   = max(float(h.get("safety_impact") or 0.2) for h in route_hazards)
    total_delay  = sum(int(h.get("expected_delay") or 2) for h in route_hazards)
    hazard_score = hd.compute_hazard_route_score(route_hazards)
    hazard_level = _hazard_level(hazard_score)

    return {
        "hazard_score":        hazard_score,
        "hazard_level":        hazard_level,
        "hazards_count":       len(route_hazards),
        "max_severity":        max_severity,
        "max_impact":          round(max_impact, 3),
        "expected_delay_min":  total_delay,
        "route_hazards":       route_hazards[:10],   # cap payload
        "has_critical":        any(int(h.get("severity") or 5) >= 8 for h in route_hazards),
    }


def _empty_hazard_result() -> dict:
    return {
        "hazard_score":       100.0,
        "hazard_level":       "Clear",
        "hazards_count":      0,
        "max_severity":       0,
        "max_impact":         0.0,
        "expected_delay_min": 0,
        "route_hazards":      [],
        "has_critical":       False,
    }


def _hazard_level(score: float) -> str:
    if score >= 90: return "Clear"
    if score >= 70: return "Low"
    if score >= 50: return "Moderate"
    if score >= 30: return "High"
    return "Critical"


# ─── Enrich routes with hazard data ──────────────────────────────────────────

def enrich_routes_with_hazards(
    routes: List[dict],
) -> List[dict]:
    """
    Add hazard data to each route dict.
    Upgrades ai_score to 30/20/15/10/25 formula.
    Existing keys are never removed.
    """
    # Fetch once and reuse for all routes
    active_hazards = get_active_hazards_enriched()

    max_duration = max(
        (r.get("eta_with_traffic", r.get("duration_min", 30)) for r in routes),
        default=30
    )

    for route in routes:
        coords  = route.get("coordinates") or route.get("geometry") or []
        hazard  = analyse_route_hazards(coords, active_hazards)

        route["hazard_score"]        = hazard["hazard_score"]
        route["hazard_level"]        = hazard["hazard_level"]
        route["hazards_count"]       = hazard["hazards_count"]
        route["hazard_delay_min"]    = hazard["expected_delay_min"]
        route["has_critical_hazard"] = hazard["has_critical"]
        route["route_hazards"]       = hazard["route_hazards"]

        # Final AI Score (30/20/15/10/25)
        route["ai_score"] = compute_final_route_score(
            safety_score  = float(route.get("safety_score",   50)),
            duration_min  = float(route.get("eta_with_traffic", route.get("duration_min", 15))),
            traffic_score = float(route.get("traffic_score",  70)),
            weather_score = float(route.get("weather_score",  80)),
            crowd_score   = float(route.get("crowd_score",    75)),
            hazard_score  = hazard["hazard_score"],
            max_duration  = max_duration + 10,
        )

    # Re-assign AI Recommended badge
    if routes:
        best = max(routes, key=lambda r: r.get("ai_score", 0))
        for r in routes:
            if r is best:
                r["badge"] = "⭐ AI Recommended" if r.get("type") == "Safest" \
                             else "⭐ AI Recommended (Hazard Aware)"
            elif not r.get("badge"):
                r["badge"] = ""

    return routes


# ─── Final AI Route Score (30/20/15/10/25 formula) ───────────────────────────

def compute_final_route_score(
    safety_score:  float,
    duration_min:  float,
    traffic_score: float,
    weather_score: float,
    crowd_score:   float,
    hazard_score:  float,
    max_duration:  float = 60,
) -> float:
    """
    Final weighted AI score:
      30% Safety Score
      20% Travel Time Score
      15% Traffic Score
      10% Crowd Density Score
      25% Road Hazard Score
    """
    import numpy as np
    time_score = max(0.0, 100.0 - (duration_min / max(max_duration, 1)) * 100)
    final = (
        0.30 * safety_score  +
        0.20 * time_score    +
        0.15 * traffic_score +
        0.10 * crowd_score   +
        0.25 * hazard_score
    )
    return round(float(np.clip(final, 0.0, 100.0)), 2)


# ─── Hazard alerts ────────────────────────────────────────────────────────────

def generate_hazard_alerts(routes: List[dict]) -> List[dict]:
    """
    Scan routes for hazards and generate user-facing alerts.
    """
    alerts = []

    MSG_MAP = {
        "pothole":         "🕳️ Pothole detected. Drive carefully.",
        "construction":    "🚧 Road construction ahead. Alternative route selected.",
        "accident":        "🚗 Accident reported nearby. Route recalculated.",
        "flood":           "🌊 Flooded road ahead. Avoid this route.",
        "waterlogging":    "🌊 Waterlogging detected. Avoid this road.",
        "fallen_tree":     "🌳 Fallen tree on road. Route recalculated.",
        "tree":            "🌳 Fallen tree on road. Drive carefully.",
        "closure":         "⚠️ Road closed ahead. Rerouting.",
        "road_closure":    "⚠️ Road closed ahead. Rerouting.",
        "police":          "🚓 Police blockade ahead. Expect delays.",
        "police_blockade": "🚓 Police blockade ahead. Expect delays.",
        "fire":            "🔥 Fire incident ahead. Avoid this area.",
        "electrical":      "⚡ Electrical hazard on road. Avoid.",
        "landslide":       "🪨 Landslide reported. Road may be blocked.",
        "emergency_zone":  "🚒 Emergency zone active. Route changed.",
        "damaged_road":    "🛣️ Damaged road section. Reduced speed.",
        "unsafe_path":     "🚷 Unsafe walking path. Use caution.",
    }

    for route in routes:
        hazards_count = route.get("hazards_count", 0)
        route_hazards = route.get("route_hazards", [])
        hazard_score  = route.get("hazard_score", 100.0)

        if not hazards_count or not route_hazards:
            continue

        # Find the most severe hazard
        worst = max(route_hazards, key=lambda h: int(h.get("severity") or 5))
        htype = (worst.get("hazard_type") or "other").lower()

        if hazards_count == 1:
            msg = MSG_MAP.get(htype, f"⚠️ {htype.replace('_', ' ').capitalize()} detected on route.")
        else:
            msg = f"⚠️ {hazards_count} hazards detected on your selected route. AI recommends a safer alternative."

        # Find safer alternative
        safer = next(
            (r for r in routes
             if r is not route and r.get("hazard_score", 100) > hazard_score + 10),
            None
        )
        if safer and hazards_count > 1:
            msg += f" Try {safer.get('type', 'another')} Route."

        alerts.append({
            "type":              "hazard_warning",
            "level":             "danger" if route.get("has_critical_hazard") else "warning",
            "route":             route.get("type", "Unknown"),
            "message":           msg,
            "hazards_count":     hazards_count,
            "worst_hazard_type": htype,
            "worst_severity":    int(worst.get("severity") or 5),
            "hazard_delay_min":  route.get("hazard_delay_min", 0),
            "recommended_route": safer.get("type") if safer else None,
        })

    return alerts


# ─── Segment penalty (called by route_engine) ─────────────────────────────────

def get_hazard_score_for_segment(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    active_hazards: List[dict],
) -> float:
    """Thin wrapper used by route_engine.build_graph."""
    return hd.get_segment_hazard_penalty(lat1, lon1, lat2, lon2, active_hazards)
