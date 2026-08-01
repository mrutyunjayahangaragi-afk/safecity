import os
import json
from datetime import datetime, timezone
import random

# For backward compatibility and avoiding DB errors if Supabase is unconfigured,
# we use in-memory stores as fallbacks similar to other repositories in this project.

USE_SUPABASE = os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")
if USE_SUPABASE:
    from supabase import create_client, Client
    supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    # Use service key for writes (bypasses RLS). Fall back to anon client if not set.
    _service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    _write_client: Client = create_client(os.getenv("SUPABASE_URL"), _service_key)
else:
    supabase = None
    _write_client = None

# Fallbacks
_city_metrics = {}
_city_predictions = []
_city_alerts = []
_mock_transport_cache = {}
_mock_parking_cache = {}

def save_city_metrics(metrics: dict):
    if _write_client:
        try:
            _write_client.table("city_metrics").insert(metrics).execute()
        except Exception as e:
            print(f"DB Error (city_metrics): {e}")
    else:
        _city_metrics.update(metrics)
        _city_metrics['timestamp'] = datetime.now(timezone.utc).isoformat()

def get_latest_city_metrics() -> dict:
    if supabase:
        try:
            res = supabase.table("city_metrics").select("*").order("id", desc=True).limit(1).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    return _city_metrics

def save_city_predictions(predictions: dict):
    if _write_client:
        try:
            _write_client.table("city_predictions").insert(predictions).execute()
        except Exception as e:
            print(f"DB Error (city_predictions): {e}")
    else:
        _city_predictions.append(predictions)

def save_city_alerts(alerts: list):
    if not alerts:
        return
    if _write_client:
        try:
            _write_client.table("city_alerts").insert(alerts).execute()
        except Exception as e:
            print(f"DB Error (city_alerts): {e}")
    else:
        _city_alerts.extend(alerts)

def get_active_city_alerts() -> list:
    if supabase:
        try:
            res = supabase.table("city_alerts").select("*").eq("is_active", True).order("created_at", desc=True).limit(20).execute()
            return res.data
        except Exception:
            pass
    return sorted(_city_alerts, key=lambda x: x.get('created_at', ''), reverse=True)[:20]

# Generate mock data for transport and parking if not available in DB
def _get_active_bbox():
    import city_manager as cm
    active = cm.current()
    if active:
        return active.config.bbox
    return (12.9, 13.0, 77.5, 77.7)

def _get_active_city_key():
    import city_manager as cm
    active = cm.current()
    if active:
        return active.city_key
    return "bengaluru"

def _generate_mock_transport():
    city_key = _get_active_city_key()
    if city_key in _mock_transport_cache:
        # Just update occupancies
        for t in _mock_transport_cache[city_key]:
            t['occupancy_percent'] = random.randint(20, 100)
        return _mock_transport_cache[city_key]

    transports = []
    bbox = _get_active_bbox()
    
    if city_key == "bengaluru":
        routes = ["K-1", "V-500D", "335-E", "G-3", "201", "215", "600-A", "V-335E", "201-R", "360-B"]
        metro_lines = ["Purple Line", "Green Line", "Yellow Line"]
        metro_stations = ["Majestic", "MG Road", "Indiranagar", "Baiyappanahalli", "Trinity", "Halasuru", "Cubbon Park", "Vidhana Soudha", "Sir M Visveshwaraya", "City Railway Station", "KSR", "Mysore Road", "Deepanjali Nagar", "Attiguppe", "Vijayanagar", "Hosahalli", "Magadi Road", "Krantivira Sangolli Rayanna", "Rajajinagar", "Kuvempu Road", "Srirampura", "Mantri Square Sampige Road"]
    else:
        routes = ["1Z", "218D", "47L", "9X", "116N", "299", "18C", "10H", "219", "277"]
        metro_lines = ["Red Line", "Blue Line", "Green Line"]
        metro_stations = ["Ameerpet", "Miyapur", "JNTU College", "KPHB Colony", "Kukatpally", "Balanagar", "Moosapet", "Bharat Nagar", "Erragadda", "ESI Hospital", "SR Nagar", "Punjagutta", "Irrum Manzil", "Khairatabad", "Lakdikapul", "Assembly", "Nampally", "Gandhi Bhavan", "Osmania Medical College", "MG Bus Station", "Malakpet", "New Market", "Musarambagh", "Dilsukhnagar", "Chaitanyapuri", "Victoria Memorial", "LB Nagar"]

    # Mock buses
    for i in range(50):
        transports.append({
            "id": f"bus-{i}",
            "type": "bus",
            "route": random.choice(routes),
            "latitude": random.uniform(bbox[0], bbox[1]),
            "longitude": random.uniform(bbox[2], bbox[3]),
            "occupancy_percent": random.randint(20, 100),
            "status": random.choice(["ON_TIME", "ON_TIME", "DELAYED", "EARLY"])
        })
    # Mock metro
    for i in range(20):
        transports.append({
            "id": f"metro-{i}",
            "type": "metro",
            "route": random.choice(metro_lines),
            "station": random.choice(metro_stations),
            "latitude": random.uniform(bbox[0], bbox[1]),
            "longitude": random.uniform(bbox[2], bbox[3]),
            "occupancy_percent": random.randint(60, 100),
            "status": random.choice(["ON_TIME", "ON_TIME", "DELAYED"])
        })
        
    _mock_transport_cache[city_key] = transports
    return transports

def _generate_mock_parking():
    city_key = _get_active_city_key()
    if city_key in _mock_parking_cache:
        for p in _mock_parking_cache[city_key]:
            p['occupied'] = random.randint(10, p['capacity'])
            p['occupancy_percent'] = round(p['occupied'] / p['capacity'] * 100, 1)
        return _mock_parking_cache[city_key]

    parking = []
    bbox = _get_active_bbox()
    
    if city_key == "bengaluru":
        locations = [
            "Indiranagar 100ft", "Koramangala 4th Blk", "MG Road Metro", "UB City", 
            "HSR Layout Sector 2", "Whitefield Forum", "Electronic City Ph1", "Jayanagar 4th Blk",
            "Majestic Bus Stand", "Brigade Road", "Commercial Street", "Shivajinagar Bus Stand",
            "Yeshwanthpur TTMC", "Banashankari BDA Complex", "JP Nagar Central", "Malleswaram 8th Cross",
            "Garuda Mall", "Orion Mall", "Phoenix Marketcity", "VR Bengaluru", 
            "Mantri Square", "Gopalan Arcade", "Royal Meenakshi Mall", "Vega City Mall",
            "Lalbagh West Gate", "Cubbon Park East", "Bangalore Palace", "Vidhana Soudha Parking",
            "Kempegowda Int'l Airport", "ITPL Whitefield", "Manyata Tech Park", "RMZ Ecospace"
        ]
    else:
        locations = [
            "Inorbit Mall Madhapur", "IKEA Parking", "Sarath City Capital Mall", "GVK One",
            "Forum Sujana Mall", "Gachibowli Stadium", "Charminar Multilevel", "Secunderabad Station",
            "Kacheguda Station", "Nampally Station", "Mindspace IT Park", "DLF Cyber City",
            "Salar Jung Museum", "Chowmahalla Palace", "Golconda Fort", "Hussain Sagar",
            "Lumbini Park", "NTR Gardens", "Sanjeevaiah Park", "KBR Park",
            "Jubilee Hills Check Post", "Ameerpet Metro", "Miyapur Metro", "LB Nagar Metro",
            "Dilsukhnagar Metro", "Tarnaka Metro", "Uppal Metro", "Nagole Metro",
            "Rajiv Gandhi Int'l Airport", "Banjara Hills Rd 12", "Hitech City Metro", "Raidurg Metro"
        ]

    for i in range(30):
        name = locations[i % len(locations)] + (f" Zone {i//len(locations) + 1}" if i >= len(locations) else "")
        capacity = random.randint(50, 300)
        occupied = random.randint(10, capacity)
        parking.append({
            "id": f"park-{i}",
            "name": name,
            "latitude": random.uniform(bbox[0], bbox[1]),
            "longitude": random.uniform(bbox[2], bbox[3]),
            "capacity": capacity,
            "occupied": occupied,
            "occupancy_percent": round(occupied / capacity * 100, 1),
            "is_safe": random.choice([True, True, True, False])
        })
        
    _mock_parking_cache[city_key] = parking
    return parking

def get_transport_status() -> list:
    if supabase:
        try:
            res = supabase.table("transport_status").select("*").execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return _generate_mock_transport()

def get_parking_status() -> list:
    if supabase:
        try:
            res = supabase.table("parking_status").select("*").execute()
            if res.data:
                return res.data
        except Exception:
            pass
    return _generate_mock_parking()
