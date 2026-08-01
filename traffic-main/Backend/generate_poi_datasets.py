import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import uuid

# Bounding boxes for Bengaluru and Hyderabad
BBOX_BLR = (12.8, 13.1, 77.5, 77.8)  # Bengaluru roughly
BBOX_HYD = (17.20, 17.60, 78.30, 78.65)  # Hyderabad roughly

CITIES = {
    "bengaluru": {
        "state": "karnataka",
        "bbox": BBOX_BLR,
        "parking_areas": ["MG Road", "Brigade Road", "Indiranagar", "Koramangala", "Whitefield", "Electronic City", "Hebbal", "Jayanagar", "Malleshwaram", "Yelahanka", "Marathahalli", "Bellandur", "HSR Layout", "Rajajinagar", "Banashankari"],
        "hospital_areas": ["Apollo Bannerghatta", "Manipal HAL Road", "Fortis Bannerghatta", "Victoria Hospital", "Narayana Health", "Aster CMI", "St John's", "Bowring", "Columbia Asia", "MS Ramaiah"],
        "police_areas": ["Cubbon Park", "Ashok Nagar", "Koramangala", "Whitefield", "Electronic City", "Indiranagar", "Jayanagar", "Hebbal", "BTM Layout", "Yelahanka"]
    },
    "hyderabad": {
        "state": "telangana",
        "bbox": BBOX_HYD,
        "parking_areas": ["Hitech City", "Gachibowli", "Jubilee Hills", "Banjara Hills", "Ameerpet", "Secunderabad", "Begumpet", "Charminar", "Kukatpally", "LB Nagar", "Madhapur", "Financial District", "Raidurg", "Miyapur", "Shamshabad"],
        "hospital_areas": ["Apollo Jubilee Hills", "Yashoda Somajiguda", "KIMS", "CARE Banjara Hills", "AIG", "Continental", "Sunshine", "Osmania General", "Gandhi Hospital", "NIMS"],
        "police_areas": ["Banjara Hills", "Jubilee Hills", "Madhapur", "Hitech City", "Gachibowli", "Begumpet", "Charminar", "Secunderabad", "Kukatpally", "Ameerpet"]
    }
}

def rand_latlon(bbox):
    lat = random.uniform(bbox[0], bbox[1])
    lon = random.uniform(bbox[2], bbox[3])
    return lat, lon

def generate_parking(city, city_data, num_records):
    data = []
    types = ["Multi-level", "Street", "Underground", "Open Lot", "Mall Parking"]
    for i in range(num_records):
        area = random.choice(city_data["parking_areas"])
        lat, lon = rand_latlon(city_data["bbox"])
        capacity = random.randint(50, 500)
        occupancy = random.uniform(0.1, 0.95)
        avail = int(capacity * (1 - occupancy))
        occ_pct = round(occupancy * 100, 2)
        
        # Calculate realistic safety score
        lighting = round(random.uniform(3.0, 10.0), 1)
        cctv = round(random.uniform(3.0, 10.0), 1)
        guard = random.choice([True, False, True])
        crime_fac = random.uniform(0.5, 2.0)
        
        # Base safety score
        safety = min(10.0, max(1.0, (lighting * 0.4) + (cctv * 0.4) + (2 if guard else 0) - crime_fac))
        safety = round(safety, 1)
        
        data.append({
            "id": str(uuid.uuid4()),
            "city": city,
            "parking_name": f"{area} {random.choice(['Smart Parking', 'Parking Zone', 'Transit Parking', 'Public Parking'])}",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "area": area,
            "capacity": capacity,
            "available_spaces": avail,
            "occupancy_percentage": occ_pct,
            "parking_type": random.choice(types),
            "fee_per_hour": random.choice([20, 30, 40, 50, 60]),
            "safety_score": safety,
            "lighting_score": lighting,
            "cctv_score": cctv,
            "security_guard": guard,
            "walking_distance_m": random.randint(50, 800),
            "ev_charging": random.choice([True, False]),
            "accessible_parking": random.choice([True, True, False]),
            "status": "Active" if occ_pct < 95 else "Full",
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
    return pd.DataFrame(data)

def generate_hospitals(city, city_data, num_records):
    data = []
    types = ["Government", "Private", "Multi-speciality", "Children", "Trauma Center", "Medical College", "Emergency Hospital"]
    h_names = city_data["hospital_areas"]
    
    for i in range(num_records):
        base_name = h_names[i % len(h_names)] if i < len(h_names) else f"{city.title()} {random.choice(types)}"
        lat, lon = rand_latlon(city_data["bbox"])
        beds = random.randint(100, 1000)
        
        data.append({
            "id": str(uuid.uuid4()),
            "city": city,
            "hospital_name": f"{base_name} {'Hospital' if 'Hospital' not in base_name else ''}".strip(),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "area": random.choice(city_data["parking_areas"]),
            "hospital_type": random.choice(types),
            "emergency": random.choice([True, True, False]),
            "trauma_center": random.choice([True, False]),
            "ambulance_available": random.randint(2, 20),
            "beds_available": random.randint(10, beds),
            "icu_available": random.randint(2, 50),
            "contact_number": f"+91 98{random.randint(10000000, 99999999)}",
            "average_response_time_min": random.randint(5, 25),
            "safety_rating": round(random.uniform(7.0, 10.0), 1),
            "occupancy_percentage": round(random.uniform(50.0, 98.0), 2),
            "open_24x7": True,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
    return pd.DataFrame(data)

def generate_police(city, city_data, num_records):
    data = []
    p_names = city_data["police_areas"]
    
    for i in range(num_records):
        area = random.choice(p_names)
        lat, lon = rand_latlon(city_data["bbox"])
        
        data.append({
            "id": str(uuid.uuid4()),
            "city": city,
            "station_name": f"{area} Police Station",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "area": area,
            "jurisdiction": f"{area} Sub-Division",
            "emergency_number": "100" if random.random() > 0.1 else "112",
            "women_helpdesk": random.choice([True, True, False]),
            "cyber_cell": random.choice([True, False]),
            "patrol_units": random.randint(2, 15),
            "average_response_time_min": random.randint(3, 15),
            "officers_available": random.randint(10, 50),
            "safety_rating": round(random.uniform(6.0, 9.5), 1),
            "open_24x7": True,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })
    return pd.DataFrame(data)

def main():
    base_path = "c:\\safe\\traffic-main\\Data"
    
    for city, config in CITIES.items():
        city_dir = os.path.join(base_path, config['state'], city)
        os.makedirs(city_dir, exist_ok=True)
        
        print(f"Generating datasets for {city}...")
        
        # Parking (250-300)
        df_parking = generate_parking(city, config, random.randint(250, 300))
        df_parking.to_csv(os.path.join(city_dir, "parking.csv"), index=False)
        
        # Hospitals (100-120)
        df_hospitals = generate_hospitals(city, config, random.randint(100, 120))
        df_hospitals.to_csv(os.path.join(city_dir, "hospitals.csv"), index=False)
        
        # Police (80-120)
        df_police = generate_police(city, config, random.randint(80, 120))
        df_police.to_csv(os.path.join(city_dir, "police.csv"), index=False)
        
        print(f"[{city}] Parking: {len(df_parking)}, Hospitals: {len(df_hospitals)}, Police: {len(df_police)}")

if __name__ == "__main__":
    main()
