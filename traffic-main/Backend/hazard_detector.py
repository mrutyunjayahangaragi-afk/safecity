"""
SafeRoute AI — AI Hazard Detector
====================================
AI-powered hazard confidence estimation and impact scoring.

Responsibilities
----------------
• Calculate safety impact (0-1) and expected delay (minutes) for each hazard type
• Estimate AI confidence from community reports, weather, traffic, and time-of-day
• Enrich raw hazard reports with AI-computed fields
• Provide segment-level hazard penalty for the route graph

All functions are pure (no I/O). Data comes from hazard_repository/service callers.
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime


# ─── Haversine distance (km) ──────────────────────────────────────────────────
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ─── Hazard type catalogue ────────────────────────────────────────────────────
#  Each entry: (base_safety_impact 0-1, base_delay_minutes, proximity_radius_km)
HAZARD_CATALOGUE: Dict[str, Tuple[float, int, float]] = {
    "pothole":       (0.25, 1,  0.15),
    "construction":  (0.45, 8,  0.30),
    "accident":      (0.80, 15, 0.40),
    "flood":         (0.90, 20, 0.50),
    "waterlogging":  (0.70, 10, 0.30),
    "tree":          (0.65, 8,  0.25),
    "fallen_tree":   (0.70, 10, 0.30),
    "closure":       (1.00, 30, 0.50),
    "road_closure":  (1.00, 30, 0.50),
    "police":        (0.40, 5,  0.25),
    "police_blockade": (0.50, 8, 0.30),
    "fire":          (0.95, 25, 0.50),
    "electrical":    (0.90, 10, 0.40),
    "landslide":     (1.00, 45, 0.60),
    "signal":        (0.30, 3,  0.10),
    "broken_signal": (0.35, 4,  0.15),
    "damaged_road":  (0.50, 6,  0.20),
    "unsafe_path":   (0.55, 5,  0.20),
    "emergency_zone":(0.85, 20, 0.40),
    "other":         (0.20, 2,  0.15),
}

# Icon map for frontend rendering
HAZARD_ICONS: Dict[str, str] = {
    "pothole":        "🕳️",
    "construction":   "🚧",
    "accident":       "🚗",
    "flood":          "🌊",
    "waterlogging":   "🌊",
    "tree":           "🌳",
    "fallen_tree":    "🌳",
    "closure":        "⚠️",
    "road_closure":   "⚠️",
    "police":         "🚓",
    "police_blockade":"🚓",
    "fire":           "🔥",
    "electrical":     "⚡",
    "landslide":      "🪨",
    "signal":         "🚦",
    "broken_signal":  "🚦",
    "damaged_road":   "🛣️",
    "unsafe_path":    "🚷",
    "emergency_zone": "🚒",
    "other":          "⚠️",
}

# Severity labels by score 1-10
def severity_label(severity: int) -> str:
    if severity <= 3: return "Low"
    if severity <= 5: return "Medium"
    if severity <= 7: return "High"
    return "Critical"

def severity_color(severity: int) -> str:
    if severity <= 3: return "#22C55E"
    if severity <= 5: return "#F59E0B"
    if severity <= 7: return "#EF4444"
    return "#ff0000"


# ─── Impact calculation ───────────────────────────────────────────────────────
def calculate_hazard_impact(hazard_type: str, severity: int) -> Tuple[float, int]:
    """
    Calculate the safety impact (0-1) and expected delay (minutes) for a hazard.

    Returns
    -------
    (safety_impact, delay_minutes)
    """
    base_impact, base_delay, _ = HAZARD_CATALOGUE.get(
        hazard_type.lower(), HAZARD_CATALOGUE["other"]
    )
    # Scale linearly with severity (1-10); severity=5 → multiplier=1.0
    severity_mult = max(0.4, severity / 5.0)
    final_impact  = round(min(1.0, base_impact  * severity_mult), 4)
    final_delay   = max(1, round(base_delay * severity_mult))
    return final_impact, final_delay


# ─── Proximity radius for routing ─────────────────────────────────────────────
def get_hazard_radius(hazard_type: str) -> float:
    """Return the influence radius (km) for routing penalty."""
    _, _, radius = HAZARD_CATALOGUE.get(hazard_type.lower(), HAZARD_CATALOGUE["other"])
    return radius


# ─── AI Confidence Estimation ─────────────────────────────────────────────────
def estimate_confidence(
    report: Dict,
    nearby_reports: List[Dict],
    weather_data: Optional[Dict] = None,
    traffic_data: Optional[Dict] = None,
) -> Tuple[str, float]:
    """
    Multi-factor AI confidence estimation.

    Factors (weighted)
    ------------------
    1. Community consensus  — 40%: nearby same-type reports
    2. Weather correlation  — 20%: weather matches hazard type
    3. Traffic correlation  — 15%: congestion matches hazard type
    4. Time-of-day          — 10%: night vs day plausibility
    5. Authenticated user   — 10%: auth users get slight boost
    6. Recency              — 5%:  recently reported = higher confidence

    Returns (label, score_0_to_1)
    """
    base = 0.25  # base for any community report

    hazard_type = (report.get("hazard_type") or "other").lower()
    now = datetime.utcnow()

    # ── 1. Community consensus (up to +0.40) ─────────────────────────────────
    if nearby_reports:
        same_type = [r for r in nearby_reports if
                     (r.get("hazard_type") or "").lower() == hazard_type
                     and r.get("id") != report.get("id")]
        if len(same_type) >= 4:
            base += 0.40
        elif len(same_type) >= 2:
            base += 0.25
        elif len(same_type) == 1:
            base += 0.12
        elif len(nearby_reports) >= 2:
            base += 0.05  # different types but area is known hazardous

    # ── 2. Weather correlation (up to +0.20) ──────────────────────────────────
    if weather_data:
        rainfall   = float(weather_data.get("rainfall_mm_hr",  weather_data.get("rainfall",    0)) or 0)
        flood_risk = float(weather_data.get("flood_risk",       0) or 0)
        wind_speed = float(weather_data.get("wind_speed_kmh",   weather_data.get("wind_speed",  0)) or 0)

        if hazard_type in ("flood", "waterlogging") and (rainfall > 10 or flood_risk > 0.4):
            base += 0.20
        elif hazard_type in ("flood", "waterlogging") and (rainfall > 3 or flood_risk > 0.2):
            base += 0.10
        elif hazard_type in ("fallen_tree", "tree") and wind_speed > 35:
            base += 0.15
        elif hazard_type in ("landslide",) and rainfall > 20:
            base += 0.18
        elif hazard_type in ("pothole", "damaged_road") and rainfall > 5:
            base += 0.06  # rain reveals potholes

    # ── 3. Traffic correlation (up to +0.15) ──────────────────────────────────
    if traffic_data:
        cong_label = (traffic_data.get("congestion_level") or
                      traffic_data.get("traffic_status") or "").upper()
        if hazard_type in ("accident", "construction", "closure", "road_closure") and \
                cong_label in ("HIGH", "SEVERE", "heavy", "severe"):
            base += 0.15
        elif hazard_type in ("accident",) and cong_label in ("MEDIUM", "moderate"):
            base += 0.08

    # ── 4. Time-of-day plausibility (up to +0.10) ──────────────────────────────
    hour = now.hour
    if hazard_type == "pothole" and 6 <= hour <= 20:
        base += 0.08   # potholes reported in daylight are more reliable
    elif hazard_type in ("flood", "waterlogging") and (17 <= hour <= 22 or 0 <= hour <= 6):
        base += 0.08   # evening/night flooding more plausible
    elif hazard_type in ("construction",) and 7 <= hour <= 19:
        base += 0.06
    else:
        base += 0.03   # small universal time boost

    # ── 5. Authenticated user (+0.10) ─────────────────────────────────────────
    uid = report.get("user_id")
    if uid and uid != "anonymous" and uid is not None:
        base += 0.10

    # ── 6. Recency (up to +0.05) ──────────────────────────────────────────────
    created_str = report.get("created_at") or ""
    if created_str:
        try:
            # handle both with and without timezone
            created_str_clean = created_str.replace("Z", "").split(".")[0]
            created_at = datetime.fromisoformat(created_str_clean)
            age_minutes = max(0, (now - created_at).total_seconds() / 60)
            if age_minutes < 30:
                base += 0.05
            elif age_minutes < 120:
                base += 0.02
        except Exception:
            pass

    final = round(min(1.0, base), 4)

    if final >= 0.80:
        label = "Verified"
    elif final >= 0.60:
        label = "High Confidence"
    elif final >= 0.40:
        label = "Medium Confidence"
    else:
        label = "Low Confidence"

    return label, final


# ─── Full enrichment ──────────────────────────────────────────────────────────
def enrich_report_with_ai(
    report: Dict,
    active_hazards: List[Dict],
    weather_data: Optional[Dict] = None,
    traffic_data: Optional[Dict] = None,
) -> Dict:
    """
    Enrich a hazard report dict with AI-computed fields.

    Adds
    ----
    safety_impact, expected_delay, confidence_label, confidence_score,
    verified, hazard_icon, severity_label, severity_color, proximity_radius_km
    """
    hazard_type = (report.get("hazard_type") or "other").lower()
    severity    = int(report.get("severity") or 5)

    # Impact + delay
    impact, delay = calculate_hazard_impact(hazard_type, severity)
    report["safety_impact"]  = impact
    report["expected_delay"] = delay
    report["proximity_radius_km"] = get_hazard_radius(hazard_type)

    # Decorative fields
    report["hazard_icon"]     = HAZARD_ICONS.get(hazard_type, "⚠️")
    report["severity_label"]  = severity_label(severity)
    report["severity_color"]  = severity_color(severity)

    # Find nearby hazards for confidence
    lat = float(report.get("latitude") or 0)
    lon = float(report.get("longitude") or 0)
    nearby = [
        h for h in active_hazards
        if h.get("id") != report.get("id")
        and h.get("latitude") is not None
        and haversine(lat, lon, float(h["latitude"]), float(h["longitude"])) < 0.5
    ]

    conf_label, conf_score = estimate_confidence(report, nearby, weather_data, traffic_data)
    report["confidence_label"] = conf_label
    report["confidence_score"] = conf_score

    # Auto-verify high-confidence reports
    if conf_score >= 0.80:
        report["verified"] = True

    return report


# ─── Segment hazard penalty (for route_engine graph) ─────────────────────────
def get_segment_hazard_penalty(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    active_hazards: List[Dict],
) -> float:
    """
    Compute the routing penalty for a graph edge based on nearby active hazards.

    Returns a penalty value to add to the edge cost (0.0 if no hazards nearby).
    """
    penalty = 0.0
    mid_lat = (lat1 + lat2) / 2
    mid_lon = (lon1 + lon2) / 2

    for h in active_hazards:
        h_lat = h.get("latitude")
        h_lon = h.get("longitude")
        if h_lat is None or h_lon is None:
            continue

        radius = h.get("proximity_radius_km") or get_hazard_radius(
            (h.get("hazard_type") or "other").lower()
        )
        dist = haversine(mid_lat, mid_lon, float(h_lat), float(h_lon))

        if dist < radius:
            impact = float(h.get("safety_impact") or 0.3)
            severity = int(h.get("severity") or 5)
            # Distance falloff: closer = larger penalty
            falloff = max(0.1, 1.0 - (dist / radius))
            # Verified hazards carry more weight
            verified_boost = 1.4 if h.get("verified") else 1.0
            penalty += impact * falloff * verified_boost * (severity / 5.0) * 0.5

    return round(min(penalty, 2.0), 4)


# ─── Route-level hazard score (0-100, higher = better = fewer hazards) ────────
def compute_hazard_route_score(route_hazards: List[Dict]) -> float:
    """
    Compute a 0-100 hazard score for a route.
    Higher = safer (fewer / less severe hazards).
    """
    if not route_hazards:
        return 100.0

    total_impact = sum(float(h.get("safety_impact") or 0.2) for h in route_hazards)
    # Diminishing penalty beyond 3 hazards
    normalized   = min(total_impact / max(len(route_hazards), 1), 1.0)
    raw_penalty  = min(total_impact * 20, 100.0)   # 5 critical hazards → ~100 penalty
    score        = round(max(0.0, 100.0 - raw_penalty), 2)
    return score
