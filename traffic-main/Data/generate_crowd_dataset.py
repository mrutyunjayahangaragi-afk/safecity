"""
SafeRoute AI — Synthetic Crowd Density Dataset Generator
Generates realistic hourly crowd density data for Bengaluru zones.

Prediction factors used:
  • Time of day / day of week
  • Nearby transit hubs (bus stops, metro stations)
  • Commercial vs residential zones
  • Historical patterns (peak hours, weekend effects)
  • Correlation with traffic congestion

Designed to be replaceable by:
  • Google Popular Times API
  • Event management APIs (BookMyShow, etc.)
  • CCTV video analytics
  • IoT crowd sensors

Run:  python generate_crowd_dataset.py
Output: karnataka/bengaluru/crowd_dataset.csv
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

random.seed(77)
np.random.seed(77)

# ─── Bengaluru crowd zones with real characteristics ─────────────────────────
# (area, lat, lon, zone_type, base_capacity, has_metro, bus_stops_count, peak_multiplier)
CROWD_ZONES = [
    ("MG Road",            12.9750, 77.6050, "commercial",   8000, True,  12, 2.5),
    ("Majestic",           12.9768, 77.5713, "transit_hub",  12000, True, 20, 3.2),
    ("Koramangala",        12.9352, 77.6245, "residential",  5000, False,  8, 2.0),
    ("Silk Board",         12.9165, 77.6101, "transit",      7000, False, 15, 2.8),
    ("Indiranagar",        12.9716, 77.6412, "commercial",   6000, True,  10, 2.2),
    ("Whitefield",         12.9698, 77.7499, "tech_park",    9000, False, 12, 2.6),
    ("Electronic City",    12.8452, 77.6602, "tech_park",    10000, False, 8, 2.4),
    ("Hebbal",             13.0358, 77.5970, "commercial",   4000, False,  6, 1.8),
    ("Yelahanka",          13.1006, 77.5964, "residential",  3000, False,  5, 1.6),
    ("Marathahalli",       12.9591, 77.6971, "commercial",   6500, False, 10, 2.3),
    ("Bannerghatta Road",  12.8993, 77.5975, "residential",  4500, False,  7, 1.9),
    ("Shivajinagar",       12.9840, 77.5975, "commercial",   5500, True,   9, 2.1),
    ("Jayanagar",          12.9258, 77.5838, "residential",  4000, False,  8, 1.8),
    ("Rajajinagar",        12.9940, 77.5524, "residential",  3500, False,  6, 1.7),
    ("Domlur",             12.9609, 77.6387, "mixed",        4500, False,  7, 2.0),
    ("Chickpet",           12.9675, 77.5773, "market",       7000, False, 11, 2.7),
    ("BTM Layout",         12.9165, 77.6080, "residential",  5000, False,  9, 2.0),
    ("KR Puram",           12.9979, 77.6963, "transit",      5500, True,  10, 2.3),
    ("Nagawara",           13.0340, 77.6180, "residential",  3500, False,  5, 1.7),
    ("JP Nagar",           12.8973, 77.5967, "residential",  4000, False,  7, 1.8),
]

CROWD_LEVELS = ["Low", "Moderate", "High", "Extreme"]

DAYS_OF_WEEK = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def hourly_crowd_factor(hour: int, zone_type: str, is_weekend: bool) -> float:
    """Return normalised crowd factor 0–1 for a given hour and zone type."""

    if zone_type in ("tech_park",):
        # Office hours peak
        if is_weekend:
            profile = {7:0.05,8:0.08,9:0.10,10:0.12,11:0.10,12:0.08,13:0.10,
                       14:0.08,15:0.06,16:0.05,17:0.05,18:0.04,19:0.04,20:0.03,
                       21:0.02,22:0.02,23:0.01,0:0.01,1:0.01,2:0.01,3:0.01,4:0.01,5:0.02,6:0.03}
        else:
            profile = {7:0.25,8:0.75,9:0.95,10:0.90,11:0.85,12:0.60,13:0.55,
                       14:0.85,15:0.88,16:0.80,17:0.85,18:0.90,19:0.60,20:0.30,
                       21:0.15,22:0.08,23:0.04,0:0.02,1:0.02,2:0.02,3:0.02,4:0.02,5:0.10,6:0.18}

    elif zone_type == "transit_hub":
        # High throughout commute hours
        if is_weekend:
            profile = {7:0.30,8:0.50,9:0.60,10:0.65,11:0.70,12:0.75,13:0.72,
                       14:0.70,15:0.68,16:0.70,17:0.75,18:0.80,19:0.70,20:0.55,
                       21:0.40,22:0.28,23:0.18,0:0.10,1:0.08,2:0.06,3:0.05,4:0.08,5:0.15,6:0.22}
        else:
            profile = {7:0.55,8:0.90,9:0.88,10:0.72,11:0.65,12:0.70,13:0.68,
                       14:0.65,15:0.68,16:0.72,17:0.92,18:0.95,19:0.80,20:0.62,
                       21:0.42,22:0.28,23:0.18,0:0.10,1:0.06,2:0.05,3:0.04,4:0.06,5:0.15,6:0.30}

    elif zone_type == "market":
        profile = {7:0.20,8:0.40,9:0.65,10:0.80,11:0.85,12:0.82,13:0.78,
                   14:0.80,15:0.82,16:0.88,17:0.90,18:0.92,19:0.85,20:0.72,
                   21:0.50,22:0.30,23:0.15,0:0.05,1:0.03,2:0.02,3:0.02,4:0.04,5:0.10,6:0.15}
        if is_weekend:
            profile = {k: min(1.0, v * 1.2) for k, v in profile.items()}

    elif zone_type == "commercial":
        if is_weekend:
            profile = {7:0.05,8:0.12,9:0.25,10:0.50,11:0.68,12:0.75,13:0.72,
                       14:0.70,15:0.72,16:0.75,17:0.80,18:0.82,19:0.78,20:0.65,
                       21:0.45,22:0.28,23:0.14,0:0.06,1:0.04,2:0.03,3:0.02,4:0.03,5:0.04,6:0.05}
        else:
            profile = {7:0.10,8:0.30,9:0.55,10:0.65,11:0.70,12:0.72,13:0.68,
                       14:0.65,15:0.68,16:0.72,17:0.82,18:0.88,19:0.78,20:0.55,
                       21:0.35,22:0.20,23:0.10,0:0.05,1:0.03,2:0.02,3:0.02,4:0.03,5:0.06,6:0.08}

    else:  # residential, mixed, transit
        if is_weekend:
            profile = {7:0.12,8:0.22,9:0.32,10:0.42,11:0.50,12:0.55,13:0.52,
                       14:0.50,15:0.52,16:0.55,17:0.62,18:0.68,19:0.65,20:0.55,
                       21:0.40,22:0.28,23:0.16,0:0.08,1:0.05,2:0.04,3:0.03,4:0.04,5:0.07,6:0.10}
        else:
            profile = {7:0.30,8:0.60,9:0.55,10:0.45,11:0.42,12:0.48,13:0.46,
                       14:0.42,15:0.44,16:0.48,17:0.68,18:0.72,19:0.65,20:0.52,
                       21:0.38,22:0.24,23:0.14,0:0.06,1:0.04,2:0.03,3:0.02,4:0.04,5:0.12,6:0.20}

    return profile.get(hour % 24, 0.3)


def crowd_level_label(score: float) -> str:
    if score < 0.25:  return "Low"
    if score < 0.55:  return "Moderate"
    if score < 0.80:  return "High"
    return "Extreme"


def estimated_people(score: float, capacity: int) -> int:
    return max(5, int(capacity * score * np.random.uniform(0.85, 1.15)))


def generate_records():
    records = []
    start_date = datetime(2024, 1, 1)

    for day_offset in range(30):
        date      = start_date + timedelta(days=day_offset)
        day_name  = DAYS_OF_WEEK[date.weekday()]
        is_weekend = date.weekday() >= 5

        for area, lat, lon, zone_type, capacity, has_metro, bus_count, peak_mult in CROWD_ZONES:
            for hour in range(24):
                base_factor = hourly_crowd_factor(hour, zone_type, is_weekend)

                # Metro boost during peak hours
                metro_boost = 0.0
                if has_metro and ((7 <= hour <= 10) or (17 <= hour <= 21)):
                    metro_boost = 0.08

                # Bus stop proximity adds baseline crowd
                bus_boost = min(0.12, bus_count * 0.005)

                crowd_score = float(np.clip(
                    base_factor * peak_mult * 0.35 + metro_boost + bus_boost
                    + np.random.uniform(-0.04, 0.04),
                    0.0, 1.0
                ))

                level  = crowd_level_label(crowd_score)
                people = estimated_people(crowd_score, capacity)
                is_night = 1 if (hour >= 20 or hour < 6) else 0

                # Safety concern: isolated + night
                isolation_risk = float(np.clip(
                    (1.0 - crowd_score) * (0.5 if is_night else 0.2), 0.0, 1.0
                ))

                # Ovecrowding risk: extreme + confined space
                overcrowd_risk = float(np.clip(
                    crowd_score * (1.2 if zone_type == "transit_hub" else 0.8), 0.0, 1.0
                ))

                lat_j = round(lat + np.random.uniform(-0.004, 0.004), 6)
                lon_j = round(lon + np.random.uniform(-0.004, 0.004), 6)

                records.append({
                    "area":             area,
                    "latitude":         lat_j,
                    "longitude":        lon_j,
                    "zone_type":        zone_type,
                    "date":             date.strftime("%Y-%m-%d"),
                    "day_of_week":      day_name,
                    "hour":             hour,
                    "is_weekend":       int(is_weekend),
                    "is_night":         is_night,
                    "crowd_score":      round(crowd_score, 3),
                    "crowd_level":      level,
                    "estimated_people": people,
                    "capacity":         capacity,
                    "utilisation_pct":  round(crowd_score * 100, 1),
                    "has_metro":        int(has_metro),
                    "bus_stops_nearby": bus_count,
                    "isolation_risk":   round(isolation_risk, 3),
                    "overcrowd_risk":   round(overcrowd_risk, 3),
                    "data_source":      "synthetic",
                })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("Generating Bengaluru crowd density dataset...")
    df = generate_records()

    out_dir  = os.path.join(os.path.dirname(__file__), "karnataka", "bengaluru")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "crowd_dataset.csv")
    df.to_csv(out_path, index=False)

    print(f"✅ Crowd dataset: {len(df):,} records → {out_path}")
    print(f"   Zones   : {df['area'].nunique()}")
    print(f"   Levels  :\n{df['crowd_level'].value_counts()}")
    print(f"   Avg score    : {df['crowd_score'].mean():.3f}")
    print(f"   Avg people   : {df['estimated_people'].mean():.0f}")
    print(f"   Peak records : {(df['crowd_level'].isin(['High','Extreme'])).sum():,}")
