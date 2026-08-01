"""
SafeRoute AI — Live Data Service
==================================
Unified live data layer implementing the hybrid architecture:

  Priority 1 → Live API  (Open-Meteo, Overpass/OSM)
  Priority 2 → Local dataset  (existing CSV files)
  Priority 3 → Synthetic estimate  (always available)

APIs used (all free, no keys required)
---------------------------------------
  Open-Meteo   https://open-meteo.com/          — live weather
  Overpass API https://overpass-api.de/          — OSM POI queries
  Nominatim    https://nominatim.openstreetmap.org — reverse geocoding

Design
------
• Every public function returns the SAME schema regardless of data source.
• Cache keys include lat/lon/hour so stale data is never served silently.
• All network calls have a short timeout; failures silently fall back.
• Existing modules (weather_repository, traffic_repository, crowd_repository)
  are NOT modified — this module sits on top and enriches their output.
"""

import time
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing   import Optional, List, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)

# ─── In-process cache ─────────────────────────────────────────────────────────
_cache: Dict[str, Dict] = {}

CACHE_TTL = {
    "weather":    300,    # 5 min
    "overpass":   1800,   # 30 min — POI data changes slowly
    "traffic":    120,    # 2 min
    "reverse":    3600,   # 1 hr
}

def _cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() - entry["ts"] > entry["ttl"]:
        del _cache[key]
        return None
    return entry["data"]

def _cache_set(key: str, data: Any, ttl: int = 300):
    _cache[key] = {"data": data, "ts": time.time(), "ttl": ttl}

def _cache_key(*parts) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


# ─── HTTP helper ──────────────────────────────────────────────────────────────
def _get_json(url: str, timeout: int = 8) -> Optional[Any]:
    """Fetch JSON from a URL, return None on any failure."""
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SafeRouteAI/2.0 (smart-city-navigation)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            import json
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug(f"HTTP fetch failed [{url[:60]}]: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE WEATHER  (Open-Meteo — free, no API key)
# ═══════════════════════════════════════════════════════════════════════════════

def get_live_weather(lat: float, lon: float) -> dict:
    """
    Fetch current + hourly weather from Open-Meteo.
    Falls back to weather_repository local data if API fails.

    Returns a dict compatible with weather_service.analyse_route_weather output.
    """
    key = _cache_key("weather", round(lat, 2), round(lon, 2))
    cached = _cache_get(key)
    if cached:
        cached["cache_hit"] = True
        return cached

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,"
        "weather_code,wind_speed_10m,visibility"
        "&hourly=precipitation_probability,visibility"
        "&timezone=Asia%2FKolkata"
        "&forecast_days=1"
    )

    data = _get_json(url)
    if data and "current" in data:
        result = _parse_open_meteo(data, lat, lon)
        _cache_set(key, result, CACHE_TTL["weather"])
        return result

    # Fallback to local dataset
    logger.info(f"Open-Meteo unavailable — using local weather fallback for ({lat},{lon})")
    return _weather_fallback(lat, lon)


def _wmo_to_condition(code: int) -> str:
    """Map WMO weather code to SafeRoute condition label."""
    if code == 0:                     return "Clear"
    if code in (1, 2, 3):            return "Cloudy"
    if code in (45, 48):             return "Fog"
    if code in (51, 53, 55):         return "Light Rain"
    if code in (61, 63, 80, 81):     return "Moderate Rain"
    if code in (65, 82):             return "Heavy Rain"
    if code in (95, 96, 99):         return "Thunderstorm"
    if code in (71, 73, 75, 77):     return "Clear"   # snow → treat as clear for India
    return "Cloudy"


def _parse_open_meteo(data: dict, lat: float, lon: float) -> dict:
    cur  = data.get("current", {})
    temp = float(cur.get("temperature_2m", 25))
    hum  = float(cur.get("relative_humidity_2m", 60))
    rain = float(cur.get("precipitation", 0))
    wmo  = int(cur.get("weather_code", 0))
    wind = float(cur.get("wind_speed_10m", 10))
    vis_raw = float(cur.get("visibility", 10000))
    vis_km  = round(min(vis_raw / 1000.0, 12.0), 1)

    condition    = _wmo_to_condition(wmo)
    vis_score    = round(min(vis_km / 12.0, 1.0), 3)
    flood_risk   = round(min(rain / 30.0, 1.0), 3)
    slip         = round(min(0.05 + rain / 40.0, 1.0), 3)
    sev          = round(max(0.0, min((rain / 40.0) + (1 - vis_score) * 0.3, 1.0)), 3)
    weather_score= round((1.0 - sev) * 100, 2)

    def _vis_lbl(v):
        if v >= 8: return "Excellent"
        if v >= 5: return "Good"
        if v >= 2: return "Moderate"
        return "Poor"

    WEATHER_META = {
        "Clear":         {"emoji":"☀️",  "color":"#f0c040"},
        "Cloudy":        {"emoji":"🌤",  "color":"#a0a0b0"},
        "Light Rain":    {"emoji":"🌧",  "color":"#5588cc"},
        "Moderate Rain": {"emoji":"🌧",  "color":"#3366bb"},
        "Heavy Rain":    {"emoji":"⛈",  "color":"#1144aa"},
        "Thunderstorm":  {"emoji":"🌩",  "color":"#cc2222"},
        "Fog":           {"emoji":"🌫",  "color":"#9090a0"},
        "Strong Wind":   {"emoji":"💨",  "color":"#d4a020"},
        "Flood":         {"emoji":"🌊",  "color":"#001188"},
    }
    meta = WEATHER_META.get(condition, {"emoji":"☀️","color":"#f0c040"})

    return {
        "source":              "open-meteo",
        "cache_hit":           False,
        "latitude":            lat,
        "longitude":           lon,
        "weather_condition":   condition,
        "weather_label":       condition,
        "weather_emoji":       meta["emoji"],
        "weather_color":       meta["color"],
        "weather_safe":        condition in ("Clear","Cloudy","Light Rain"),
        "temperature_c":       round(temp, 1),
        "humidity_pct":        round(hum, 1),
        "rainfall_mm_hr":      round(rain, 2),
        "wind_speed_kmh":      round(wind, 1),
        "visibility_km":       vis_km,
        "visibility_score":    vis_score,
        "visibility_label":    _vis_lbl(vis_km),
        "flood_risk":          flood_risk,
        "flood_label":         "Low" if flood_risk<0.2 else "Moderate" if flood_risk<0.5 else "High",
        "road_slipperiness":   slip,
        "road_condition":      "Dry" if slip<0.15 else "Wet" if slip<0.35 else "Slippery",
        "weather_severity":    sev,
        "weather_risk_score":  round(sev * 100, 2),
        "weather_score":       weather_score,
        "waterlogging_risk":   round(flood_risk * 0.85, 3),
        "updated_at":          datetime.now(timezone.utc).isoformat(),
    }


def _weather_fallback(lat: float, lon: float) -> dict:
    """Return local dataset weather or synthetic estimate."""
    try:
        import weather_repository as wr
        hour = datetime.now().hour
        pw   = wr.get_point_weather(lat, lon, hour)
        if pw:
            pw["source"] = "local_dataset_fallback"
            return pw
    except Exception:
        pass
    return {
        "source":            "synthetic_fallback",
        "weather_condition": "Clear",
        "weather_label":     "Clear",
        "weather_emoji":     "☀️",
        "weather_color":     "#f0c040",
        "weather_safe":      True,
        "temperature_c":     25.0,
        "humidity_pct":      60.0,
        "rainfall_mm_hr":    0.0,
        "wind_speed_kmh":    10.0,
        "visibility_km":     10.0,
        "visibility_score":  1.0,
        "visibility_label":  "Excellent",
        "flood_risk":        0.05,
        "flood_label":       "Low",
        "road_slipperiness": 0.05,
        "road_condition":    "Dry",
        "weather_severity":  0.05,
        "weather_risk_score":5.0,
        "weather_score":     95.0,
        "waterlogging_risk": 0.05,
        "updated_at":        datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OVERPASS / OSM  — Points of Interest
# ═══════════════════════════════════════════════════════════════════════════════

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

_OSM_QUERIES = {
    "police":     '[amenity=police]',
    "hospital":   '[amenity=hospital]',
    "bus_stop":   '[highway=bus_stop]',
    "metro":      '[railway=station][station=subway]',
    "parking":    '[amenity=parking]',
    "fuel":       '[amenity=fuel]',
    "school":     '[amenity=school]',
    "charging":   '[amenity=charging_station]',
    "pharmacy":   '[amenity=pharmacy]',
    "fire":       '[amenity=fire_station]',
}

_POI_ICONS = {
    "police":"🚓", "hospital":"🏥", "bus_stop":"🚌", "metro":"🚇",
    "parking":"🅿️", "fuel":"⛽", "school":"🏫", "charging":"⚡",
    "pharmacy":"💊", "fire":"🚒",
}


def get_live_poi(
    lat: float,
    lon: float,
    poi_type: str,
    radius_m: int = 2000,
    limit: int = 30,
) -> List[dict]:
    """
    Fetch nearby points of interest from OpenStreetMap via Overpass API.
    Falls back to local hardcoded data for police/hospitals in Bengaluru.

    Returns [{lat, lon, name, type, icon, source}, ...]
    """
    if poi_type not in _OSM_QUERIES:
        return []

    key = _cache_key("overpass", poi_type, round(lat, 2), round(lon, 2), radius_m)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    query = _OSM_QUERIES[poi_type]
    overpass_query = (
        f"[out:json][timeout:10];"
        f"(node{query}(around:{radius_m},{lat},{lon});"
        f"way{query}(around:{radius_m},{lat},{lon}););"
        f"out center {limit};"
    )
    import urllib.parse
    url = _OVERPASS_URL + "?data=" + urllib.parse.quote(overpass_query)

    data = _get_json(url, timeout=12)
    if data and "elements" in data:
        results = _parse_overpass(data["elements"], poi_type)
        _cache_set(key, results, CACHE_TTL["overpass"])
        logger.info(f"Overpass {poi_type}: {len(results)} results near ({lat:.3f},{lon:.3f})")
        return results

    # Fallback to static Bengaluru data
    fallback = _poi_fallback(lat, lon, poi_type, limit)
    _cache_set(key, fallback, 300)  # cache fallback for 5 min
    return fallback


def _parse_overpass(elements: list, poi_type: str) -> List[dict]:
    results = []
    icon    = _POI_ICONS.get(poi_type, "📍")
    for el in elements:
        tags = el.get("tags", {})
        name = (tags.get("name") or tags.get("name:en") or
                tags.get("amenity") or tags.get("highway") or poi_type.replace("_", " ").title())
        # Coordinates
        if el.get("type") == "node":
            clat, clon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center", {})
            clat, clon = c.get("lat"), c.get("lon")
        if clat is None or clon is None:
            continue
        results.append({
            "lat":    round(float(clat), 6),
            "lon":    round(float(clon), 6),
            "name":   name,
            "type":   poi_type,
            "icon":   icon,
            "phone":  tags.get("phone", ""),
            "source": "openstreetmap",
        })
    return results


def _poi_fallback(lat: float, lon: float, poi_type: str, limit: int) -> List[dict]:
    """
    Static fallback data for Bengaluru police stations and hospitals.
    For other types or cities, returns an empty list gracefully.
    """
    import city_manager as cm
    active = cm.current()
    city_key = active.city_key if active else "bengaluru"

    STATIC = {
        "bengaluru": {
            "police": [
                {"lat":12.9760,"lon":77.5930,"name":"Cubbon Park Police Station"},
                {"lat":12.9675,"lon":77.5773,"name":"Chickpet Police Station"},
                {"lat":12.9352,"lon":77.6245,"name":"Koramangala Police Station"},
                {"lat":12.9716,"lon":77.6412,"name":"Indiranagar Police Station"},
                {"lat":13.0358,"lon":77.5970,"name":"Hebbal Police Station"},
                {"lat":12.9698,"lon":77.7499,"name":"Whitefield Police Station"},
                {"lat":12.8452,"lon":77.6602,"name":"Electronic City Police Station"},
            ],
            "hospital": [
                {"lat":12.9660,"lon":77.5737,"name":"Victoria Hospital"},
                {"lat":12.9578,"lon":77.6477,"name":"Manipal Hospital"},
                {"lat":12.9398,"lon":77.5970,"name":"NIMHANS"},
                {"lat":13.0210,"lon":77.5702,"name":"MS Ramaiah Hospital"},
                {"lat":12.9279,"lon":77.6271,"name":"Fortis Hospital Koramangala"},
            ]
        },
        "hyderabad": {
            "police": [
                {"lat": 17.4315, "lon": 78.4069, "name": "Jubilee Hills Police Station"},
                {"lat": 17.4435, "lon": 78.3772, "name": "Madhapur Police Station"},
                {"lat": 17.3616, "lon": 78.4747, "name": "Charminar Police Station"},
                {"lat": 17.4401, "lon": 78.3489, "name": "Gachibowli Police Station"},
                {"lat": 17.4399, "lon": 78.4983, "name": "Secunderabad Police Station"}
            ],
            "hospital": [
                {"lat": 17.4156, "lon": 78.4347, "name": "Apollo Hospitals"},
                {"lat": 17.4375, "lon": 78.4482, "name": "KIMS Hospital"},
                {"lat": 17.3934, "lon": 78.4323, "name": "Care Hospitals"},
                {"lat": 17.4401, "lon": 78.3489, "name": "AIG Hospitals"},
                {"lat": 17.3616, "lon": 78.4747, "name": "Osmania General Hospital"}
            ]
        }
    }

    city_static = STATIC.get(city_key, STATIC["bengaluru"])
    records = city_static.get(poi_type, [])

    icon    = _POI_ICONS.get(poi_type, "📍")
    return [
        {**r, "type": poi_type, "icon": icon, "phone": "", "source": "static_fallback"}
        for r in records[:limit]
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE TRAFFIC ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def get_live_traffic_estimate(lat: float, lon: float, hour: Optional[int] = None) -> dict:
    """
    Attempt to get traffic from free APIs; fall back to local dataset + synthetic.

    Currently implements intelligent estimation from:
      - Hour of day (peak/off-peak)
      - Day of week
      - Local traffic dataset lookup

    When TomTom or HERE free-tier keys are available, plug them in here.
    """
    if hour is None:
        hour = datetime.now().hour

    key = _cache_key("traffic", round(lat, 2), round(lon, 2), hour)
    cached = _cache_get(key)
    if cached:
        cached["cache_hit"] = True
        return cached

    # Try local dataset first
    try:
        import traffic_repository as tr
        seg = tr.get_segment_traffic(lat, lon, hour)
        if seg and seg.get("data_source") == "local_dataset":
            result = {
                **seg,
                "source":     "local_dataset",
                "cache_hit":  False,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            _cache_set(key, result, CACHE_TTL["traffic"])
            return result
    except Exception:
        pass

    # Synthetic intelligent estimate
    result = _synthetic_traffic(lat, lon, hour)
    _cache_set(key, result, CACHE_TTL["traffic"])
    return result


def _synthetic_traffic(lat: float, lon: float, hour: int) -> dict:
    """Realistic traffic estimate from time-of-day patterns."""
    is_peak   = (7 <= hour <= 10) or (17 <= hour <= 21)
    is_night  = hour >= 22 or hour < 5
    congestion = 0.72 if is_peak else (0.15 if is_night else 0.38)
    congestion = float(np.clip(congestion + np.random.uniform(-0.05, 0.05), 0.05, 0.95))
    speed      = round(max(5.0, 40.0 * (1 - congestion * 0.85)), 1)
    delay      = round(max(0.0, (1.2 / max(speed, 1) - 1.2 / 40.0) * 60), 1)

    label = ("severe" if congestion > 0.75 else
             "heavy"  if congestion > 0.55 else
             "moderate" if congestion > 0.30 else "low")

    return {
        "source":             "synthetic_estimate",
        "cache_hit":          False,
        "congestion_level":   round(congestion, 3),
        "average_speed_kmh":  speed,
        "delay_minutes":      delay,
        "traffic_percentage": round(congestion * 100, 1),
        "peak_hour":          is_peak,
        "traffic_status":     label,
        "updated_at":         datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# REVERSE GEOCODING  (Nominatim)
# ═══════════════════════════════════════════════════════════════════════════════

def reverse_geocode(lat: float, lon: float) -> dict:
    """Convert coordinates to a human-readable address using Nominatim."""
    key = _cache_key("reverse", round(lat, 4), round(lon, 4))
    cached = _cache_get(key)
    if cached:
        return cached

    url = (
        f"https://nominatim.openstreetmap.org/reverse"
        f"?lat={lat}&lon={lon}&format=json&accept-language=en"
    )
    data = _get_json(url)
    if data and "address" in data:
        addr = data["address"]
        label = (addr.get("road") or addr.get("neighbourhood") or
                 addr.get("suburb") or addr.get("city") or
                 data.get("display_name","").split(",")[0])
        result = {
            "label":    label,
            "city":     addr.get("city") or addr.get("town") or addr.get("village",""),
            "state":    addr.get("state",""),
            "postcode": addr.get("postcode",""),
            "full":     data.get("display_name",""),
            "source":   "nominatim",
        }
        _cache_set(key, result, CACHE_TTL["reverse"])
        return result

    return {"label": f"{lat:.4f},{lon:.4f}", "city": "", "state": "", "source": "fallback"}


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def get_cache_stats() -> dict:
    now = time.time()
    live  = sum(1 for e in _cache.values() if now - e["ts"] <= e["ttl"])
    stale = len(_cache) - live
    return {
        "total_entries": len(_cache),
        "live_entries":  live,
        "stale_entries": stale,
    }

def clear_cache(prefix: Optional[str] = None):
    global _cache
    if prefix is None:
        _cache = {}
    else:
        _cache = {k: v for k, v in _cache.items() if not k.startswith(prefix)}
