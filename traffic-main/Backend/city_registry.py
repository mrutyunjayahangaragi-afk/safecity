"""
Safe Route AI — City Registry
Single source of truth for all supported cities.

To add a new city:
  1. Add an entry to CITY_REGISTRY below.
  2. Place the dataset CSV at  data/<state>/<city_key>.csv
  3. No backend code changes needed.

Structure
---------
CITY_REGISTRY = {
    "<state_key>": {
        "label": "Display Name",
        "cities": {
            "<city_key>": CityConfig(...)
        }
    }
}
"""

from dataclasses import dataclass, field
from typing      import Dict, Tuple, List, Optional


@dataclass
class CityConfig:
    label:        str                    # Display name  e.g. "Bengaluru"
    state:        str                    # Parent state key e.g. "karnataka"
    center_lat:   float                  # Map center latitude
    center_lon:   float                  # Map center longitude
    bbox:         Tuple[float,float,float,float]  # (min_lat, max_lat, min_lon, max_lon)
    zoom:         int   = 12             # Leaflet default zoom
    dataset_file: str   = ""             # relative to data/ folder, auto-filled if blank
    # Default waypoints shown in the UI origin/destination dropdowns
    waypoints:    List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.dataset_file:
            # Auto-derive: data/<state>/<city_label>.csv
            state_dir = self.state.replace(" ", "_").title()
            city_file = self.label.replace(" ", "_") + ".csv"
            self.dataset_file = f"{state_dir}/{city_file}"


# ─── Registry ────────────────────────────────────────────────────────────────
CITY_REGISTRY: Dict[str, Dict] = {

    "karnataka": {
        "label": "Karnataka",
        "cities": {
            "bengaluru": CityConfig(
                label      = "Bengaluru",
                state      = "karnataka",
                center_lat = 12.9716,
                center_lon = 77.5946,
                bbox       = (12.80, 13.15, 77.45, 77.80),
                zoom       = 12,
                # Keep exact same waypoints as original frontend
                waypoints  = [
                    {"label": "City Centre (MG Road)",   "lat": 12.9716, "lon": 77.5946},
                    {"label": "Majestic / KSR Station",  "lat": 12.9768, "lon": 77.5713},
                    {"label": "Indiranagar",             "lat": 12.9716, "lon": 77.6412},
                    {"label": "Marathahalli",            "lat": 12.9591, "lon": 77.6971},
                    {"label": "Hebbal",                  "lat": 13.0358, "lon": 77.5970},
                    {"label": "Yelahanka",               "lat": 13.1006, "lon": 77.5964},
                    {"label": "Whitefield",              "lat": 12.9698, "lon": 77.7499},
                    {"label": "Koramangala",             "lat": 12.9352, "lon": 77.6245},
                    {"label": "BTM Layout",              "lat": 12.9165, "lon": 77.6101},
                    {"label": "Jayanagar",               "lat": 12.9258, "lon": 77.5838},
                    {"label": "Electronic City",         "lat": 12.8452, "lon": 77.6602},
                    {"label": "Bannerghatta Road",       "lat": 12.8993, "lon": 77.5975},
                    {"label": "Shivajinagar",            "lat": 12.9840, "lon": 77.5975},
                    {"label": "Domlur",                  "lat": 12.9609, "lon": 77.6387},
                ],
            ),
            "mysuru": CityConfig(
                label      = "Mysuru",
                state      = "karnataka",
                center_lat = 12.2958,
                center_lon = 76.6394,
                bbox       = (12.20, 12.40, 76.55, 76.75),
                zoom       = 13,
                waypoints  = [
                    {"label": "Mysuru Palace",     "lat": 12.3052, "lon": 76.6552},
                    {"label": "Chamundi Hills",    "lat": 12.2723, "lon": 76.6705},
                    {"label": "City Bus Stand",    "lat": 12.2958, "lon": 76.6394},
                    {"label": "Saraswathipuram",   "lat": 12.3161, "lon": 76.6367},
                    {"label": "Vijayanagar",       "lat": 12.3301, "lon": 76.6193},
                    {"label": "Kuvempunagar",      "lat": 12.2852, "lon": 76.6228},
                ],
            ),
            "hubballi": CityConfig(
                label      = "Hubballi",
                state      = "karnataka",
                center_lat = 15.3647,
                center_lon = 75.1240,
                bbox       = (15.28, 15.45, 75.05, 75.22),
                zoom       = 13,
                waypoints  = [
                    {"label": "Hubballi Station",  "lat": 15.3647, "lon": 75.1240},
                    {"label": "Dharwad Centre",    "lat": 15.4589, "lon": 75.0078},
                    {"label": "Unkal",             "lat": 15.3820, "lon": 75.1350},
                    {"label": "Gokul Road",        "lat": 15.3743, "lon": 75.1091},
                ],
            ),
            "mangaluru": CityConfig(
                label      = "Mangaluru",
                state      = "karnataka",
                center_lat = 12.9141,
                center_lon = 74.8560,
                bbox       = (12.82, 13.02, 74.77, 74.94),
                zoom       = 13,
                waypoints  = [
                    {"label": "Mangaluru Central", "lat": 12.8698, "lon": 74.8428},
                    {"label": "Hampankatta",       "lat": 12.8707, "lon": 74.8428},
                    {"label": "Kadri",             "lat": 12.8947, "lon": 74.8510},
                    {"label": "Bejai",             "lat": 12.8780, "lon": 74.8600},
                ],
            ),
        },
    },

    "maharashtra": {
        "label": "Maharashtra",
        "cities": {
            "mumbai": CityConfig(
                label      = "Mumbai",
                state      = "maharashtra",
                center_lat = 19.0760,
                center_lon = 72.8777,
                bbox       = (18.85, 19.35, 72.75, 73.00),
                zoom       = 12,
                waypoints  = [
                    {"label": "CST Station",      "lat": 18.9400, "lon": 72.8347},
                    {"label": "Dadar",            "lat": 19.0178, "lon": 72.8478},
                    {"label": "Bandra",           "lat": 19.0596, "lon": 72.8295},
                    {"label": "Andheri",          "lat": 19.1136, "lon": 72.8697},
                    {"label": "Borivali",         "lat": 19.2307, "lon": 72.8567},
                    {"label": "Colaba",           "lat": 18.9067, "lon": 72.8147},
                    {"label": "Worli",            "lat": 19.0176, "lon": 72.8139},
                    {"label": "Thane",            "lat": 19.2183, "lon": 72.9781},
                ],
            ),
            "pune": CityConfig(
                label      = "Pune",
                state      = "maharashtra",
                center_lat = 18.5204,
                center_lon = 73.8567,
                bbox       = (18.40, 18.65, 73.75, 74.00),
                zoom       = 12,
                waypoints  = [
                    {"label": "Shivajinagar",     "lat": 18.5308, "lon": 73.8474},
                    {"label": "Kothrud",          "lat": 18.5074, "lon": 73.8077},
                    {"label": "Hinjewadi",        "lat": 18.5912, "lon": 73.7384},
                    {"label": "Kharadi",          "lat": 18.5562, "lon": 73.9418},
                    {"label": "Hadapsar",         "lat": 18.5089, "lon": 73.9260},
                    {"label": "Pimpri",           "lat": 18.6279, "lon": 73.8009},
                ],
            ),
        },
    },

    "telangana": {
        "label": "Telangana",
        "cities": {
            "hyderabad": CityConfig(
                label      = "Hyderabad",
                state      = "telangana",
                center_lat = 17.3850,
                center_lon = 78.4867,
                bbox       = (17.20, 17.60, 78.30, 78.65),
                zoom       = 12,
                waypoints  = [
                    {"label": "Charminar",        "lat": 17.3616, "lon": 78.4747},
                    {"label": "Hitech City",      "lat": 17.4435, "lon": 78.3772},
                    {"label": "Banjara Hills",    "lat": 17.4156, "lon": 78.4347},
                    {"label": "Secunderabad",     "lat": 17.4399, "lon": 78.4983},
                    {"label": "Gachibowli",       "lat": 17.4401, "lon": 78.3489},
                    {"label": "LB Nagar",         "lat": 17.3444, "lon": 78.5528},
                ],
            ),
        },
    },

    "tamil_nadu": {
        "label": "Tamil Nadu",
        "cities": {
            "chennai": CityConfig(
                label      = "Chennai",
                state      = "tamil_nadu",
                center_lat = 13.0827,
                center_lon = 80.2707,
                bbox       = (12.90, 13.25, 80.15, 80.40),
                zoom       = 12,
                waypoints  = [
                    {"label": "Chennai Central",  "lat": 13.0827, "lon": 80.2707},
                    {"label": "T Nagar",          "lat": 13.0418, "lon": 80.2341},
                    {"label": "Anna Nagar",       "lat": 13.0850, "lon": 80.2101},
                    {"label": "Velachery",        "lat": 12.9815, "lon": 80.2180},
                    {"label": "Adyar",            "lat": 13.0012, "lon": 80.2565},
                    {"label": "Tambaram",         "lat": 12.9249, "lon": 80.1000},
                ],
            ),
        },
    },

    "delhi": {
        "label": "Delhi",
        "cities": {
            "delhi": CityConfig(
                label      = "Delhi",
                state      = "delhi",
                center_lat = 28.6139,
                center_lon = 77.2090,
                bbox       = (28.40, 28.88, 76.85, 77.35),
                zoom       = 11,
                waypoints  = [
                    {"label": "Connaught Place",  "lat": 28.6315, "lon": 77.2167},
                    {"label": "Karol Bagh",       "lat": 28.6514, "lon": 77.1907},
                    {"label": "Lajpat Nagar",     "lat": 28.5700, "lon": 77.2400},
                    {"label": "Rohini",           "lat": 28.7041, "lon": 77.1025},
                    {"label": "Dwarka",           "lat": 28.5921, "lon": 77.0460},
                    {"label": "Saket",            "lat": 28.5244, "lon": 77.2066},
                ],
            ),
        },
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_city(state_key: str, city_key: str) -> Optional[CityConfig]:
    """Return a CityConfig or None."""
    state = CITY_REGISTRY.get(state_key.lower())
    if not state:
        return None
    return state["cities"].get(city_key.lower())


def list_states() -> List[Dict]:
    """Return [{key, label}, ...] for all states."""
    return [{"key": k, "label": v["label"]} for k, v in CITY_REGISTRY.items()]


def list_cities(state_key: str) -> List[Dict]:
    """Return [{key, label, center_lat, center_lon, zoom}, ...] for a state."""
    state = CITY_REGISTRY.get(state_key.lower(), {})
    cities = state.get("cities", {})
    return [
        {
            "key":        ck,
            "label":      cfg.label,
            "center_lat": cfg.center_lat,
            "center_lon": cfg.center_lon,
            "zoom":       cfg.zoom,
            "has_dataset": True,   # flag extended in app.py based on file existence
        }
        for ck, cfg in cities.items()
    ]


def resolve_city_from_coords(lat: float, lon: float) -> Optional[Dict]:
    """
    GPS fallback: find which city's bounding box contains the given coords.
    Returns {"state_key": ..., "city_key": ..., "config": CityConfig} or None.
    """
    for state_key, state_data in CITY_REGISTRY.items():
        for city_key, cfg in state_data["cities"].items():
            min_lat, max_lat, min_lon, max_lon = cfg.bbox
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return {"state_key": state_key, "city_key": city_key, "config": cfg}
    return None
