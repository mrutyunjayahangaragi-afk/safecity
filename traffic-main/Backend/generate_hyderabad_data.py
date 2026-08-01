import os
import json
import random
import csv
import pandas as pd
import numpy as np

STATE = "telangana"
CITY = "hyderabad"
BBOX = (17.20, 17.60, 78.30, 78.65) # min_lat, max_lat, min_lon, max_lon

# Key Hotspots (Lat, Lon)
HOTSPOTS = {
    "Hitech City": (17.4435, 78.3772),
    "Charminar": (17.3616, 78.4747),
    "Banjara Hills": (17.4156, 78.4347),
    "Secunderabad": (17.4399, 78.4983),
    "Gachibowli": (17.4401, 78.3489),
    "Jubilee Hills": (17.4315, 78.4069),
    "Ameerpet": (17.4375, 78.4482),
    "Kukatpally": (17.4948, 78.3996),
    "LB Nagar": (17.3444, 78.5528),
    "Dilsukhnagar": (17.3688, 78.5307),
    "Mehdipatnam": (17.3934, 78.4323),
    "Tolichowki": (17.3986, 78.4137),
    "Miyapur": (17.4968, 78.3614),
    "Financial District": (17.4143, 78.3441),
    "Nanakramguda": (17.4168, 78.3431),
    "Uppal": (17.3984, 78.5583),
    "Raidurg": (17.4243, 78.3804),
    "Shamshabad": (17.2570, 78.4067)
}

CRIME_TYPES = ["Theft", "Chain Snatching", "Robbery", "Eve Teasing", "Vehicle Theft", "Assault", "Pickpocketing", "Cybercrime", "Drug Offense", "Vandalism"]

def generate_random_coord(center_lat, center_lon, radius_km=3.0):
    # Approximation: 1 deg lat ~= 111 km, 1 deg lon ~= 111 * cos(lat)
    radius_deg_lat = radius_km / 111.0
    radius_deg_lon = radius_km / (111.0 * np.cos(np.radians(center_lat)))
    
    u = random.random()
    v = random.random()
    w = radius_deg_lat * np.sqrt(u)
    t = 2 * np.pi * v
    lat = center_lat + w * np.cos(t)
    lon = center_lon + w * np.sin(t) * (radius_deg_lon / radius_deg_lat)
    
    # Ensure within bbox
    lat = max(BBOX[0], min(BBOX[1], lat))
    lon = max(BBOX[2], min(BBOX[3], lon))
    return lat, lon

def generate_crime_data(output_path, num_records=3000):
    data = []
    hotspot_names = list(HOTSPOTS.keys())
    for _ in range(num_records):
        # 80% clustered around hotspots, 20% random
        if random.random() < 0.8:
            area = random.choice(hotspot_names)
            center = HOTSPOTS[area]
            lat, lon = generate_random_coord(center[0], center[1], radius_km=2.5)
        else:
            area = "Unknown"
            lat = random.uniform(BBOX[0], BBOX[1])
            lon = random.uniform(BBOX[2], BBOX[3])
            
        crime = random.choice(CRIME_TYPES)
        severity = round(random.uniform(2.0, 10.0), 1)
        hour = random.randint(0, 23)
        is_night = 1 if (hour >= 20 or hour < 6) else 0
        
        data.append([lat, lon, crime, severity, hour, area, is_night])
        
    df = pd.DataFrame(data, columns=["latitude", "longitude", "crime_type", "crime_severity", "hour", "area", "is_night"])
    df.to_csv(output_path, index=False)
    print(f"Generated {num_records} crime records at {output_path}")

def generate_traffic_data(output_path, num_records=2000):
    data = []
    for _ in range(num_records):
        lat = random.uniform(BBOX[0], BBOX[1])
        lon = random.uniform(BBOX[2], BBOX[3])
        congestion_level = random.randint(0, 100)
        speed = max(5, 60 - (congestion_level / 2)) # Approx logic
        hour = random.randint(0, 23)
        data.append([lat, lon, congestion_level, speed, hour])
    
    df = pd.DataFrame(data, columns=["latitude", "longitude", "congestion_level", "speed_kmh", "hour"])
    df.to_csv(output_path, index=False)
    print(f"Generated {num_records} traffic records at {output_path}")

def generate_weather_data(output_path, num_records=500):
    data = []
    for _ in range(num_records):
        lat = random.uniform(BBOX[0], BBOX[1])
        lon = random.uniform(BBOX[2], BBOX[3])
        temp = round(random.uniform(20.0, 42.0), 1)
        precip = round(random.uniform(0.0, 50.0), 1)
        visibility = round(random.uniform(1.0, 10.0), 1)
        data.append([lat, lon, temp, precip, visibility])
        
    df = pd.DataFrame(data, columns=["latitude", "longitude", "temperature", "precipitation", "visibility"])
    df.to_csv(output_path, index=False)
    print(f"Generated {num_records} weather records at {output_path}")
    
def generate_crowd_data(output_path, num_records=1500):
    data = []
    for _ in range(num_records):
        lat = random.uniform(BBOX[0], BBOX[1])
        lon = random.uniform(BBOX[2], BBOX[3])
        density = random.randint(10, 1000)
        hour = random.randint(0, 23)
        data.append([lat, lon, density, hour])
        
    df = pd.DataFrame(data, columns=["latitude", "longitude", "density", "hour"])
    df.to_csv(output_path, index=False)
    print(f"Generated {num_records} crowd records at {output_path}")

def main():
    base_dir = os.path.join("c:\\safe\\traffic-main\\Data", STATE, CITY)
    os.makedirs(base_dir, exist_ok=True)
    
    # Write config
    config = {
        "city_key": CITY,
        "state_key": STATE,
        "label": "Hyderabad",
        "bbox": BBOX
    }
    with open(os.path.join(base_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=4)
        
    generate_crime_data(os.path.join(base_dir, "crime_dataset.csv"))
    generate_traffic_data(os.path.join(base_dir, "traffic_dataset.csv"))
    generate_weather_data(os.path.join(base_dir, "weather_dataset.csv"))
    generate_crowd_data(os.path.join(base_dir, "crowd_dataset.csv"))
    
    print("Hyderabad datasets generated successfully.")

if __name__ == "__main__":
    main()
