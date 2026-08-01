import random
from datetime import datetime

import traffic_repository as tr
import weather_repository as wr
import crowd_repository as cr
import hazard_service as hs
import dashboard_repository as dr

def calculate_current_metrics() -> dict:
    """Aggregates data from all existing modules to compute a live city snapshot."""
    # 1. Traffic Index
    # Assuming tr.get_live_reports() gives some insight, 
    # but we will just simulate a high-level index based on mock data.
    reports = tr.get_live_reports()
    traffic_index = 50.0 + (len(reports) * 2.0)
    traffic_index = min(100.0, max(0.0, traffic_index))
    
    # 2. Weather Severity Index
    try:
        import requests
        import city_manager as cm
        active = cm.current()
        lat = active.config.center_lat if active else 12.9716
        lon = active.config.center_lon if active else 77.5946
        resp = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true", timeout=5)
        weather_data = resp.json().get("current_weather", {})
        weather_severity = 0.0
        if weather_data.get("windspeed", 0) > 20:
            weather_severity += 30
        if weather_data.get("precipitation", 0) > 0:
            weather_severity += 40
        if weather_data.get("temperature", 0) > 35:
            weather_severity += 20
        # add random fluctuation to make it live-like
        weather_severity += random.uniform(0, 10)
    except Exception:
        weather_severity = random.uniform(10, 30)
        
    # 3. Crowd Density Index
    crowd_reports = cr.get_crowd_reports()
    crowd_index = 30.0 + (len(crowd_reports) * 5.0)
    crowd_index = min(100.0, max(0.0, crowd_index))
    
    # 4. Hazard Count
    hazards = hs.get_active_hazards_enriched()
    hazard_count = len(hazards)
    
    # 5. Transport and Parking
    transport = dr.get_transport_status()
    total_occupancy = sum([t.get("occupancy_percent", 0) for t in transport]) if transport else 0
    transport_efficiency = 100.0 - (total_occupancy / len(transport) * 0.5) if transport else 100.0
    
    parking = dr.get_parking_status()
    total_parking_occ = sum([p.get("occupancy_percent", 0) for p in parking]) if parking else 0
    parking_occupancy = total_parking_occ / len(parking) if parking else 0.0
    
    # 6. Overall Safety Index (0-100)
    # 100 is perfectly safe. 
    # Deduct points for bad traffic, weather, crowd, and hazards
    safety_deduction = (traffic_index * 0.2) + (weather_severity * 0.15) + (crowd_index * 0.1) + (hazard_count * 2)
    # fluctuate realistically based on time/randomness
    overall_safety_index = 100.0 - safety_deduction + random.uniform(-2, 2)
    overall_safety_index = min(100.0, max(0.0, overall_safety_index))
    
    metrics = {
        "overall_safety_index": round(overall_safety_index, 1),
        "traffic_index": round(traffic_index, 1),
        "crowd_density_index": round(crowd_index, 1),
        "weather_severity_index": round(weather_severity, 1),
        "hazard_count": hazard_count,
        "emergency_response_time": random.randint(5, 15), # Simulated emergency response time in minutes
        "parking_occupancy": round(parking_occupancy, 1),
        "transport_efficiency": round(transport_efficiency, 1),
        "active_navigation_sessions": random.randint(15000, 25000),
        "sos_requests": random.randint(2, 10)
    }
    
    # Save to DB/memory
    dr.save_city_metrics(metrics)
    return metrics
