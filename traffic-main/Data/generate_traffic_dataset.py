"""
SafeRoute AI — Synthetic Traffic Dataset Generator
Generates realistic road-segment traffic data for Bengaluru.

Designed so live traffic APIs (Google Maps, HERE, TomTom, OpenStreetMap)
can replace or augment this dataset without changing the backend schema.

Run:  python generate_traffic_dataset.py
Output: karnataka/bengaluru/traffic_dataset.csv
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

# ─── Major Bengaluru road corridors ──────────────────────────────────────────
ROAD_SEGMENTS = [
    # (road_name, area, center_lat, center_lon, road_type, capacity_vph, width_m)
    ("MG Road",                "City Centre",     12.9750, 77.6050, "arterial",  3200, 30),
    ("Brigade Road",           "City Centre",     12.9725, 77.6083, "arterial",  2800, 24),
    ("Residency Road",         "City Centre",     12.9692, 77.6020, "arterial",  2600, 22),
    ("Majestic-KSR Corridor",  "Majestic",        12.9768, 77.5713, "arterial",  4000, 36),
    ("Tumkur Road NH-48",      "Rajajinagar",     12.9940, 77.5524, "national",  5000, 45),
    ("Outer Ring Road (N)",    "Hebbal",          13.0358, 77.5970, "ring_road", 6000, 60),
    ("Outer Ring Road (E)",    "Marathahalli",    12.9591, 77.6971, "ring_road", 6000, 60),
    ("Sarjapur Road",          "Koramangala",     12.9352, 77.6245, "arterial",  3500, 30),
    ("Hosur Road NH-44",       "Electronic City", 12.8452, 77.6602, "national",  5500, 48),
    ("Bannerghatta Road",      "Bannerghatta",    12.8993, 77.5975, "arterial",  3200, 28),
    ("Kanakpura Road",         "Jayanagar",       12.9258, 77.5838, "arterial",  2800, 26),
    ("100 Feet Road Indiranagar","Indiranagar",   12.9716, 77.6412, "arterial",  3000, 30),
    ("Old Airport Road",       "Domlur",          12.9609, 77.6387, "arterial",  2800, 24),
    ("Whitefield Road",        "Whitefield",      12.9698, 77.7499, "arterial",  3200, 30),
    ("Bellary Road NH-44",     "Yelahanka",       13.1006, 77.5964, "national",  5000, 45),
    ("ITPL Main Road",         "Whitefield",      12.9828, 77.7272, "arterial",  3000, 28),
    ("Marathahalli Bridge",    "Marathahalli",    12.9542, 77.7011, "bridge",    2400, 20),
    ("KR Puram Bridge",        "KR Puram",        12.9979, 77.6963, "bridge",    2200, 18),
    ("Silk Board Junction",    "BTM Layout",      12.9165, 77.6101, "junction",  3500, 32),
    ("Hebbal Flyover",         "Hebbal",          13.0450, 77.5920, "flyover",   3800, 28),
    ("JP Nagar 7th Phase",     "JP Nagar",        12.8973, 77.5967, "arterial",  2400, 22),
    ("Koramangala 5th Block",  "Koramangala",     12.9279, 77.6271, "arterial",  2600, 24),
    ("Shivajinagar Circle",    "Shivajinagar",    12.9840, 77.5975, "junction",  3200, 28),
    ("Chickpet Main Road",     "Chickpet",        12.9675, 77.5773, "arterial",  2800, 22),
    ("BTM Layout Main Road",   "BTM Layout",      12.9165, 77.6080, "arterial",  2600, 22),
    ("HSR Layout Sector 7",    "HSR Layout",      12.9116, 77.6387, "arterial",  2400, 20),
    ("Electronic City Phase 2","Electronic City", 12.8362, 77.6700, "arterial",  3000, 26),
    ("Yelahanka New Town",     "Yelahanka",       13.1006, 77.5950, "arterial",  2200, 20),
    ("Nagawara Circle",        "Nagawara",        13.0340, 77.6180, "junction",  3000, 26),
    ("Bommanahalli",           "Bommanahalli",    12.8997, 77.6388, "arterial",  2600, 22),
]

TRAFFIC_DIRECTIONS = ["both", "inbound", "outbound", "one_way"]

def is_peak_hour(hour: int) -> int:
    return 1 if (7 <= hour <= 9) or (17 <= hour <= 20) else 0

def congestion_for_hour(hour: int, road_type: str) -> float:
    """Return a realistic congestion level (0-1) based on hour and road type."""
    base = {
        "national":  0.35, "ring_road": 0.40, "arterial": 0.30,
        "junction":  0.45, "bridge":    0.50, "flyover":  0.40,
    }.get(road_type, 0.30)

    # Peak multipliers
    if 7 <= hour <= 9:
        multiplier = 2.2
    elif 17 <= hour <= 20:
        multiplier = 2.0
    elif 12 <= hour <= 14:
        multiplier = 1.3
    elif 22 <= hour or hour <= 5:
        multiplier = 0.4
    else:
        multiplier = 1.0

    noise = np.random.uniform(-0.05, 0.05)
    return float(np.clip(base * multiplier + noise, 0.05, 0.98))


def speed_from_congestion(congestion: float, road_type: str) -> float:
    """Free-flow speed reduced by congestion."""
    free_flow = {
        "national": 70, "ring_road": 60, "arterial": 40,
        "junction": 25, "bridge": 35,   "flyover": 50,
    }.get(road_type, 40)
    speed = free_flow * (1.0 - congestion * 0.85)
    return round(max(5.0, speed + np.random.uniform(-3, 3)), 1)


def delay_from_congestion(congestion: float, segment_length_km: float = 1.2) -> float:
    """Estimated delay in minutes for a segment."""
    free_speed = 40.0
    actual_speed = max(5.0, free_speed * (1.0 - congestion * 0.85))
    free_time  = (segment_length_km / free_speed) * 60
    actual_time = (segment_length_km / actual_speed) * 60
    return round(max(0.0, actual_time - free_time), 1)


def generate_records():
    records = []
    start_date = datetime(2024, 1, 1)

    for road_name, area, center_lat, center_lon, road_type, capacity, width in ROAD_SEGMENTS:
        # Generate 24-hour profile for 30 days
        for day_offset in range(30):
            date = start_date + timedelta(days=day_offset)
            for hour in range(24):
                congestion = congestion_for_hour(hour, road_type)
                avg_speed  = speed_from_congestion(congestion, road_type)
                delay      = delay_from_congestion(congestion)

                vehicle_density = round(capacity * congestion * np.random.uniform(0.8, 1.2) / 24, 1)
                traffic_pct     = round(congestion * 100, 1)
                signal_count    = random.randint(1, 8) if road_type in ("arterial", "junction") else random.randint(0, 3)
                accident_prob   = round(np.clip(0.02 + 0.15 * congestion + 0.05 * (1 if hour >= 20 else 0), 0.01, 0.35), 3)

                # Add slight lat/lon jitter per segment for spatial variety
                lat = round(center_lat + np.random.uniform(-0.003, 0.003), 6)
                lon = round(center_lon + np.random.uniform(-0.003, 0.003), 6)

                records.append({
                    "road_name":         road_name,
                    "area":              area,
                    "latitude":          lat,
                    "longitude":         lon,
                    "road_type":         road_type,
                    "hour":              hour,
                    "date":              date.strftime("%Y-%m-%d"),
                    "congestion_level":  round(congestion, 3),
                    "average_speed_kmh": avg_speed,
                    "vehicle_density":   vehicle_density,
                    "delay_minutes":     delay,
                    "traffic_percentage": traffic_pct,
                    "road_capacity_vph": capacity,
                    "road_width_m":      width,
                    "signal_count":      signal_count,
                    "peak_hour":         is_peak_hour(hour),
                    "accident_probability": accident_prob,
                    "traffic_direction": random.choice(TRAFFIC_DIRECTIONS),
                    "is_road_closed":    0,
                    "weather_condition": random.choice(["clear", "clear", "clear", "cloudy", "rainy"]),
                    "data_source":       "synthetic",  # replaced by "live_api" when real data plugged in
                })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("Generating Bengaluru traffic dataset...")
    df = generate_records()

    out_dir = os.path.join(os.path.dirname(__file__), "karnataka", "bengaluru")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "traffic_dataset.csv")
    df.to_csv(out_path, index=False)

    print(f"✅ Traffic dataset: {len(df):,} records → {out_path}")
    print(f"   Roads: {df['road_name'].nunique()}")
    print(f"   Avg congestion: {df['congestion_level'].mean():.3f}")
    print(f"   Peak hour records: {df['peak_hour'].sum():,}")
    print(df.groupby("road_type")["congestion_level"].mean().round(3))
