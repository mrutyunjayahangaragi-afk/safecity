"""
SafeRoute AI — Synthetic Weather Dataset Generator
Generates realistic hourly weather data for Bengaluru road segments.

Designed to be replaceable by live weather APIs
(OpenWeatherMap, IMD, AccuWeather) without changing the backend schema.

Run:  python generate_weather_dataset.py
Output: karnataka/bengaluru/weather_dataset.csv
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

random.seed(99)
np.random.seed(99)

# ─── Bengaluru weather zones (areas with distinct flood/rain risk) ────────────
WEATHER_ZONES = [
    # (area, center_lat, center_lon, flood_risk_base, rain_freq)
    ("Koramangala",       12.9352, 77.6245, 0.65, 0.55),   # low-lying, flood-prone
    ("Silk Board",        12.9165, 77.6101, 0.72, 0.58),   # notorious waterlogging
    ("BTM Layout",        12.9165, 77.6080, 0.68, 0.55),
    ("Majestic",          12.9768, 77.5713, 0.40, 0.45),
    ("MG Road",           12.9750, 77.6050, 0.30, 0.40),
    ("Indiranagar",       12.9716, 77.6412, 0.35, 0.42),
    ("Whitefield",        12.9698, 77.7499, 0.45, 0.50),
    ("Electronic City",   12.8452, 77.6602, 0.50, 0.52),
    ("Hebbal",            13.0358, 77.5970, 0.38, 0.44),
    ("Yelahanka",         13.1006, 77.5964, 0.28, 0.38),
    ("Marathahalli",      12.9591, 77.6971, 0.55, 0.50),
    ("Bannerghatta Road", 12.8993, 77.5975, 0.42, 0.46),
    ("Shivajinagar",      12.9840, 77.5975, 0.35, 0.43),
    ("Jayanagar",         12.9258, 77.5838, 0.32, 0.41),
    ("Rajajinagar",       12.9940, 77.5524, 0.30, 0.40),
    ("Domlur",            12.9609, 77.6387, 0.38, 0.43),
    ("Chickpet",          12.9675, 77.5773, 0.45, 0.48),
    ("KR Puram",          12.9979, 77.6963, 0.52, 0.50),
    ("Nagawara",          13.0340, 77.6180, 0.36, 0.42),
    ("JP Nagar",          12.8973, 77.5967, 0.40, 0.45),
]

# Bengaluru monthly rain profile (mm/month avg)
MONTHLY_RAIN = {
    1:  5,  2:  8,  3: 15,  4: 45,  5: 110,
    6: 85, 7: 115, 8: 135, 9: 185, 10: 170,
   11: 55, 12: 20
}

WEATHER_CONDITIONS = [
    "Clear", "Cloudy", "Light Rain", "Moderate Rain",
    "Heavy Rain", "Thunderstorm", "Fog", "Strong Wind", "Flood"
]

# Condition → (rainfall_mm_hr, visibility_km, wind_kmh, humidity, severity)
CONDITION_PROFILES = {
    "Clear":         (0.0,  12.0,  8.0, 45.0, 0.05),
    "Cloudy":        (0.0,   9.0, 12.0, 62.0, 0.10),
    "Light Rain":    (2.5,   7.0, 15.0, 78.0, 0.25),
    "Moderate Rain": (8.0,   4.5, 20.0, 85.0, 0.45),
    "Heavy Rain":    (20.0,  2.0, 30.0, 92.0, 0.70),
    "Thunderstorm":  (35.0,  1.2, 55.0, 95.0, 0.88),
    "Fog":           (0.2,   0.5,  5.0, 90.0, 0.55),
    "Strong Wind":   (1.0,   8.0, 65.0, 60.0, 0.50),
    "Flood":         (50.0,  1.0, 25.0, 97.0, 0.95),
}


def condition_for_hour(hour: int, month: int, rain_freq: float) -> str:
    """Pick a weather condition weighted by hour, season, and zone rain frequency."""
    monthly_factor = MONTHLY_RAIN[month] / 185.0   # normalised (Sep is peak)

    if 22 <= hour or hour <= 5:
        weights = {
            "Clear":  max(0.1, 0.55 - monthly_factor * 0.3),
            "Cloudy": 0.20,
            "Fog":    min(0.25, 0.05 + (1 - monthly_factor) * 0.15),
            "Light Rain":    monthly_factor * rain_freq * 0.25,
            "Moderate Rain": monthly_factor * rain_freq * 0.15,
            "Heavy Rain":    monthly_factor * rain_freq * 0.10,
            "Thunderstorm":  monthly_factor * rain_freq * 0.05,
            "Strong Wind":   0.03,
            "Flood":         monthly_factor * rain_freq * 0.02,
        }
    elif 7 <= hour <= 9 or 17 <= hour <= 20:   # peak hours
        weights = {
            "Clear":  max(0.1, 0.45 - monthly_factor * 0.25),
            "Cloudy": 0.22,
            "Fog":    0.03,
            "Light Rain":    monthly_factor * rain_freq * 0.30,
            "Moderate Rain": monthly_factor * rain_freq * 0.18,
            "Heavy Rain":    monthly_factor * rain_freq * 0.12,
            "Thunderstorm":  monthly_factor * rain_freq * 0.06,
            "Strong Wind":   0.04,
            "Flood":         monthly_factor * rain_freq * 0.03,
        }
    else:
        weights = {
            "Clear":  max(0.1, 0.50 - monthly_factor * 0.28),
            "Cloudy": 0.22,
            "Fog":    0.04,
            "Light Rain":    monthly_factor * rain_freq * 0.28,
            "Moderate Rain": monthly_factor * rain_freq * 0.16,
            "Heavy Rain":    monthly_factor * rain_freq * 0.10,
            "Thunderstorm":  monthly_factor * rain_freq * 0.05,
            "Strong Wind":   0.03,
            "Flood":         monthly_factor * rain_freq * 0.02,
        }

    conditions = list(weights.keys())
    w = np.array([max(0.001, v) for v in weights.values()], dtype=float)
    w /= w.sum()
    return np.random.choice(conditions, p=w)


def road_slipperiness(condition: str, rainfall: float) -> float:
    base = {"Clear": 0.05, "Cloudy": 0.08, "Light Rain": 0.30,
            "Moderate Rain": 0.50, "Heavy Rain": 0.72, "Thunderstorm": 0.85,
            "Fog": 0.15, "Strong Wind": 0.12, "Flood": 0.95}
    slip = base.get(condition, 0.20) + rainfall / 200.0
    return round(float(np.clip(slip + np.random.uniform(-0.03, 0.03), 0.0, 1.0)), 3)


def visibility_score(vis_km: float) -> float:
    """Convert raw visibility (km) to a 0–1 score (1 = perfect)."""
    return round(float(np.clip(vis_km / 12.0, 0.0, 1.0)), 3)


def temperature_for_hour(hour: int, month: int) -> float:
    """Realistic Bengaluru temperature °C by hour and month."""
    monthly_avg = {
        1: 21, 2: 23, 3: 27, 4: 30, 5: 29,
        6: 25, 7: 23, 8: 24, 9: 24, 10: 24,
       11: 22, 12: 21
    }
    base = monthly_avg[month]
    if 14 <= hour <= 16:
        offset = 4.0
    elif 6 <= hour <= 8:
        offset = -4.0
    elif 22 <= hour or hour <= 4:
        offset = -3.0
    else:
        offset = 0.0
    return round(base + offset + np.random.uniform(-1.5, 1.5), 1)


def generate_records():
    records = []
    start_date = datetime(2024, 1, 1)

    for day_offset in range(30):
        date = start_date + timedelta(days=day_offset)
        month = date.month

        for area, center_lat, center_lon, flood_risk_base, rain_freq in WEATHER_ZONES:
            for hour in range(24):
                condition = condition_for_hour(hour, month, rain_freq)
                profile   = CONDITION_PROFILES[condition]
                rain_base, vis_base, wind_base, hum_base, severity_base = profile

                # Add realistic noise
                rainfall   = round(max(0.0, rain_base  + np.random.uniform(-rain_base*0.2, rain_base*0.3)), 2)
                visibility = round(max(0.2, vis_base   + np.random.uniform(-0.8, 0.8)), 1)
                wind_speed = round(max(0.0, wind_base  + np.random.uniform(-5, 5)), 1)
                humidity   = round(float(np.clip(hum_base + np.random.uniform(-5, 5), 30, 100)), 1)
                temperature= temperature_for_hour(hour, month)

                # Flood risk: base zone risk amplified by rainfall
                monthly_factor = MONTHLY_RAIN[month] / 185.0
                flood_risk = float(np.clip(
                    flood_risk_base * monthly_factor * (1 + rainfall / 30.0)
                    + np.random.uniform(-0.05, 0.05), 0.0, 1.0
                ))

                # Waterlogging probability
                waterlogging = float(np.clip(
                    flood_risk * 0.85 + (rainfall / 50.0) * 0.15
                    + np.random.uniform(-0.03, 0.03), 0.0, 1.0
                ))

                slipperiness    = road_slipperiness(condition, rainfall)
                vis_score       = visibility_score(visibility)
                weather_severity= float(np.clip(severity_base + np.random.uniform(-0.05, 0.05), 0.0, 1.0))

                # Small lat/lon jitter per area per day
                lat = round(center_lat + np.random.uniform(-0.005, 0.005), 6)
                lon = round(center_lon + np.random.uniform(-0.005, 0.005), 6)

                records.append({
                    "area":              area,
                    "latitude":          lat,
                    "longitude":         lon,
                    "date":              date.strftime("%Y-%m-%d"),
                    "hour":              hour,
                    "month":             month,
                    "weather_condition": condition,
                    "rainfall_mm_hr":    rainfall,
                    "visibility_km":     visibility,
                    "visibility_score":  vis_score,
                    "wind_speed_kmh":    wind_speed,
                    "humidity_pct":      humidity,
                    "temperature_c":     temperature,
                    "flood_risk":        round(flood_risk, 3),
                    "waterlogging_risk": round(waterlogging, 3),
                    "road_slipperiness": slipperiness,
                    "weather_severity":  round(weather_severity, 3),
                    "is_night":          1 if (hour >= 20 or hour < 6) else 0,
                    "data_source":       "synthetic",
                })

    return pd.DataFrame(records)


if __name__ == "__main__":
    print("Generating Bengaluru weather dataset...")
    df = generate_records()

    out_dir  = os.path.join(os.path.dirname(__file__), "karnataka", "bengaluru")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "weather_dataset.csv")
    df.to_csv(out_path, index=False)

    print(f"✅ Weather dataset: {len(df):,} records → {out_path}")
    print(f"   Areas : {df['area'].nunique()}")
    print(f"   Conditions:\n{df['weather_condition'].value_counts()}")
    print(f"   Avg flood risk  : {df['flood_risk'].mean():.3f}")
    print(f"   Avg visibility  : {df['visibility_km'].mean():.1f} km")
    print(f"   Avg rain (mm/hr): {df['rainfall_mm_hr'].mean():.2f}")
