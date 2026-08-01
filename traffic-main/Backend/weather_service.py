"""
SafeRoute AI — Weather Service
=================================
Business logic for weather-aware routing.

Responsibilities
----------------
• Compute weather risk score for a route or point
• Enrich route dicts with weather data (mirrors traffic_service pattern)
• Generate live weather alerts for dangerous conditions
• Provide weather layer data for the map
• Implement 40/25/20/15 final AI scoring formula

This module is stateless — all data comes from weather_repository.
It does NOT modify route_engine, safety_score, risk_model, or traffic_service.
"""

from __future__ import annotations

import numpy as np
from typing import List, Optional

import weather_repository as wr


# ─── Weather condition metadata ───────────────────────────────────────────────
WEATHER_META = {
    "Clear":         {"emoji": "☀️",  "color": "#f0c040", "label": "Clear",          "safe": True},
    "Cloudy":        {"emoji": "🌤",  "color": "#a0a0b0", "label": "Cloudy",         "safe": True},
    "Light Rain":    {"emoji": "🌧",  "color": "#5588cc", "label": "Light Rain",     "safe": True},
    "Moderate Rain": {"emoji": "🌧",  "color": "#3366bb", "label": "Moderate Rain",  "safe": False},
    "Heavy Rain":    {"emoji": "⛈",  "color": "#1144aa", "label": "Heavy Rain",     "safe": False},
    "Thunderstorm":  {"emoji": "🌩",  "color": "#cc2222", "label": "Thunderstorm",   "safe": False},
    "Fog":           {"emoji": "🌫",  "color": "#9090a0", "label": "Fog",            "safe": False},
    "Strong Wind":   {"emoji": "💨",  "color": "#d4a020", "label": "Strong Wind",    "safe": False},
    "Flood":         {"emoji": "🌊",  "color": "#001188", "label": "Flood Warning",  "safe": False},
}

# ─── Visibility label ─────────────────────────────────────────────────────────
def _visibility_label(vis_km: float) -> str:
    if vis_km >= 8.0:  return "Excellent"
    if vis_km >= 5.0:  return "Good"
    if vis_km >= 2.0:  return "Moderate"
    if vis_km >= 0.5:  return "Poor"
    return "Very Poor"

# ─── Flood risk label ─────────────────────────────────────────────────────────
def _flood_label(risk: float) -> str:
    if risk < 0.20:  return "Low"
    if risk < 0.50:  return "Moderate"
    if risk < 0.75:  return "High"
    return "Severe"

# ─── Road condition label ────────────────────────────────────────────────────
def _road_condition_label(slipperiness: float) -> str:
    if slipperiness < 0.15:  return "Dry"
    if slipperiness < 0.35:  return "Wet"
    if slipperiness < 0.60:  return "Slippery"
    return "Hazardous"


# ─── Weather risk score (0–100, higher = worse weather) ──────────────────────

def compute_weather_risk_score(weather_point: dict) -> float:
    """
    Calculate a 0–100 weather risk score for a single location.

    Components
    ----------
    • rainfall       — 30%
    • flood_risk     — 25%
    • visibility     — 25% (inverted)
    • road_slip      — 10%
    • wind           — 10%
    """
    rainfall   = float(weather_point.get("rainfall_mm_hr",  0.0))
    flood      = float(weather_point.get("flood_risk",       0.0))
    vis_score  = float(weather_point.get("visibility_score", 1.0))  # 1 = perfect
    slip       = float(weather_point.get("road_slipperiness",0.0))
    wind       = float(weather_point.get("wind_speed_kmh",   5.0))

    # Normalise rainfall to 0–1 (50 mm/hr = saturation)
    rain_norm  = float(np.clip(rainfall / 50.0, 0.0, 1.0))
    # Normalise wind to 0–1 (80 km/h = saturation)
    wind_norm  = float(np.clip(wind / 80.0, 0.0, 1.0))
    # Visibility risk = 1 − vis_score
    vis_risk   = 1.0 - vis_score

    raw = (
        0.30 * rain_norm  +
        0.25 * flood      +
        0.25 * vis_risk   +
        0.10 * slip       +
        0.10 * wind_norm
    )
    return round(float(np.clip(raw * 100, 0.0, 100.0)), 2)


# ─── Route weather analysis ───────────────────────────────────────────────────

def analyse_route_weather(
    coordinates: List[list],
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """
    Analyse weather conditions along a route's waypoints.

    Returns a full weather summary dict for the route.
    """
    if not coordinates or len(coordinates) < 2:
        return _empty_weather_result(hour)

    sample = coordinates[::2] if len(coordinates) > 6 else coordinates

    point_results = []
    for pt in sample:
        lat, lon = float(pt[0]), float(pt[1])
        pw = wr.get_point_weather(lat, lon, hour, state_key=state_key, city_key=city_key)
        if pw:
            point_results.append(pw)

    if not point_results:
        return _empty_weather_result(hour)

    # Aggregate
    avg_rain   = float(np.mean([p["rainfall_mm_hr"]   for p in point_results]))
    avg_vis    = float(np.mean([p["visibility_km"]     for p in point_results]))
    avg_vis_sc = float(np.mean([p["visibility_score"]  for p in point_results]))
    avg_wind   = float(np.mean([p["wind_speed_kmh"]    for p in point_results]))
    avg_flood  = float(np.mean([p["flood_risk"]        for p in point_results]))
    avg_water  = float(np.mean([p["waterlogging_risk"] for p in point_results]))
    avg_slip   = float(np.mean([p["road_slipperiness"] for p in point_results]))
    avg_humid  = float(np.mean([p["humidity_pct"]      for p in point_results]))
    avg_temp   = float(np.mean([p["temperature_c"]     for p in point_results]))
    avg_sev    = float(np.mean([p["weather_severity"]  for p in point_results]))

    # Dominant condition (most severe)
    severity_order = ["Flood","Thunderstorm","Heavy Rain","Fog","Strong Wind",
                      "Moderate Rain","Light Rain","Cloudy","Clear"]
    conditions_seen = [p["weather_condition"] for p in point_results]
    dominant = next((c for c in severity_order if c in conditions_seen), "Clear")

    # Weather risk score (0–100, higher = riskier)
    worst_point = max(point_results, key=lambda p: p["weather_severity"])
    weather_risk_score = compute_weather_risk_score(worst_point)

    # Weather score for routing formula (0–100, higher = better weather)
    weather_score = round(100.0 - weather_risk_score, 2)

    meta = WEATHER_META.get(dominant, WEATHER_META["Clear"])

    return {
        "dominant_condition": dominant,
        "weather_label":      meta["label"],
        "weather_emoji":      meta["emoji"],
        "weather_color":      meta["color"],
        "weather_safe":       meta["safe"],
        "avg_rainfall_mm":    round(avg_rain, 2),
        "avg_visibility_km":  round(avg_vis, 1),
        "visibility_label":   _visibility_label(avg_vis),
        "avg_wind_kmh":       round(avg_wind, 1),
        "flood_risk":         round(avg_flood, 3),
        "flood_label":        _flood_label(avg_flood),
        "waterlogging_risk":  round(avg_water, 3),
        "road_slipperiness":  round(avg_slip, 3),
        "road_condition":     _road_condition_label(avg_slip),
        "humidity_pct":       round(avg_humid, 1),
        "temperature_c":      round(avg_temp, 1),
        "weather_severity":   round(avg_sev, 3),
        "weather_risk_score": weather_risk_score,
        "weather_score":      weather_score,   # used in 40/25/20/15 formula
        "point_count":        len(point_results),
    }


def _empty_weather_result(hour: int) -> dict:
    """Fallback when no weather data is available."""
    return {
        "dominant_condition": "Clear",
        "weather_label":      "Clear",
        "weather_emoji":      "☀️",
        "weather_color":      "#f0c040",
        "weather_safe":       True,
        "avg_rainfall_mm":    0.0,
        "avg_visibility_km":  10.0,
        "visibility_label":   "Excellent",
        "avg_wind_kmh":       8.0,
        "flood_risk":         0.05,
        "flood_label":        "Low",
        "waterlogging_risk":  0.05,
        "road_slipperiness":  0.05,
        "road_condition":     "Dry",
        "humidity_pct":       55.0,
        "temperature_c":      25.0,
        "weather_severity":   0.05,
        "weather_risk_score": 5.0,
        "weather_score":      95.0,
        "point_count":        0,
    }


# ─── Final AI Route Score (40/25/20/15 formula) ──────────────────────────────

def compute_final_route_score(
    safety_score:  float,      # 0–100
    duration_min:  float,      # minutes
    traffic_score: float,      # 0–100
    weather_score: float,      # 0–100
    max_duration:  float = 60,
) -> float:
    """
    Final weighted AI score:
      40% Safety Score
      25% Travel Time Score
      20% Traffic Score
      15% Weather Score
    """
    time_score = max(0.0, 100.0 - (duration_min / max(max_duration, 1)) * 100)
    final = (
        0.40 * safety_score  +
        0.25 * time_score    +
        0.20 * traffic_score +
        0.15 * weather_score
    )
    return round(float(np.clip(final, 0.0, 100.0)), 2)


# ─── Enrich routes with weather data ─────────────────────────────────────────

def enrich_routes_with_weather(
    routes: List[dict],
    hour:   int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> List[dict]:
    """
    Add weather data to each route dict.
    Also upgrades ai_score from 50/30/20 → 40/25/20/15 formula.
    Existing keys are never removed.
    """
    max_duration = max((r.get("eta_with_traffic", r.get("duration_min", 30)) for r in routes), default=30)

    for route in routes:
        coords  = route.get("coordinates") or route.get("geometry") or []
        weather = analyse_route_weather(coords, hour, state_key, city_key)

        # Inject weather fields
        route["weather_condition"] = weather["dominant_condition"]
        route["weather_label"]     = weather["weather_label"]
        route["weather_emoji"]     = weather["weather_emoji"]
        route["weather_color"]     = weather["weather_color"]
        route["weather_safe"]      = weather["weather_safe"]
        route["rainfall_mm"]       = weather["avg_rainfall_mm"]
        route["visibility_km"]     = weather["avg_visibility_km"]
        route["visibility_label"]  = weather["visibility_label"]
        route["flood_risk"]        = weather["flood_risk"]
        route["flood_label"]       = weather["flood_label"]
        route["road_condition"]    = weather["road_condition"]
        route["wind_speed_kmh"]    = weather["avg_wind_kmh"]
        route["temperature_c"]     = weather["temperature_c"]
        route["weather_score"]     = weather["weather_score"]
        route["weather_risk_score"]= weather["weather_risk_score"]

        # Upgrade ai_score with weather factor (40/25/20/15)
        route["ai_score"] = compute_final_route_score(
            safety_score  = float(route.get("safety_score", 50)),
            duration_min  = float(route.get("eta_with_traffic", route.get("duration_min", 15))),
            traffic_score = float(route.get("traffic_score", 70)),
            weather_score = weather["weather_score"],
            max_duration  = max_duration + 10,
        )

    # Re-assign AI Recommended badge to highest ai_score
    if routes:
        best = max(routes, key=lambda r: r.get("ai_score", 0))
        for r in routes:
            if r is best:
                suffix = ""
                if r.get("type") != "Safest":
                    suffix = " (Weather+Traffic)"
                r["badge"] = f"⭐ AI Recommended{suffix}"
            elif not r.get("badge"):
                r["badge"] = ""

    return routes


# ─── Weather alerts ───────────────────────────────────────────────────────────

def generate_weather_alerts(routes: List[dict]) -> List[dict]:
    """
    Scan routes for dangerous weather and generate user-facing alerts.
    """
    alerts = []
    DANGER_CONDITIONS = {"Heavy Rain", "Thunderstorm", "Flood", "Fog", "Strong Wind"}

    for route in routes:
        cond  = route.get("weather_condition", "Clear")
        flood = route.get("flood_risk", 0.0)
        vis   = route.get("visibility_km", 10.0)

        if cond == "Flood" or flood > 0.6:
            safer = next((r for r in routes if r is not route and r.get("flood_risk", 1) < flood), None)
            alerts.append({
                "type":    "flood_warning",
                "level":   "danger",
                "route":   route["type"],
                "message": (
                    f"🌊 Flood-prone road on {route['type']} Route. "
                    + (f"AI switched to {safer['type']} Route." if safer else "Proceed with caution.")
                ),
            })

        elif cond == "Thunderstorm":
            alerts.append({
                "type":    "storm_warning",
                "level":   "danger",
                "route":   route["type"],
                "message": f"🌩 Thunderstorm detected on {route['type']} Route. Drive with extreme caution.",
            })

        elif cond == "Heavy Rain":
            alerts.append({
                "type":    "heavy_rain",
                "level":   "warning",
                "route":   route["type"],
                "message": f"⛈ Heavy rainfall on {route['type']} Route. AI recommends Safest Route.",
            })

        elif cond == "Fog" or vis < 1.5:
            alerts.append({
                "type":    "low_visibility",
                "level":   "warning",
                "route":   route["type"],
                "message": f"🌫 Low visibility ({vis:.1f} km) on {route['type']} Route. Drive carefully.",
            })

    return alerts


# ─── Weather heatmap for frontend ────────────────────────────────────────────

def get_weather_heatmap(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
    limit: int = 200,
) -> List[dict]:
    """Return weather heatmap data for Leaflet rendering."""
    data = wr.get_weather_heatmap(hour, state_key, city_key)
    return data[:limit]


def get_weather_analytics(
    hour: int,
    state_key: str = "karnataka",
    city_key:  str = "bengaluru",
) -> dict:
    """Full weather analytics payload for dashboard."""
    stats   = wr.get_weather_stats(hour, state_key, city_key)
    trend   = wr.get_weather_daily_trend(state_key, city_key)
    reports = wr.get_weather_reports(limit=20)
    r_alerts= wr.get_road_weather_alerts(limit=20)

    return {
        "weather_stats":       stats,
        "daily_trend":         trend,
        "recent_reports":      reports,
        "road_weather_alerts": r_alerts,
        "supabase_status":     wr.get_supabase_status(),
        "hour":                hour,
    }
