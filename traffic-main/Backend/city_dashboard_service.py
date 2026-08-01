import random
import dashboard_repository as dr

def generate_ai_insights(metrics: dict, transport: list, parking: list, hazards: list, crowd: list) -> list:
    """Analyze current data and generate actionable AI City Insights."""
    alerts = []
    
    # Traffic & Congestion Insights
    if metrics.get("traffic_index", 50) > 70:
        alerts.append({
            "category": "traffic",
            "severity": "HIGH",
            "message": "Traffic congestion increasing across central zones. Recommending alternate routing.",
            "is_active": True
        })
        
    # Weather Insights
    if metrics.get("weather_severity_index", 0) > 40:
        alerts.append({
            "category": "weather",
            "severity": "MEDIUM",
            "message": "Heavy rainfall detected. Expect localized waterlogging and slower traffic speeds.",
            "is_active": True
        })
        
    # Hazard Insights
    if len(hazards) >= 3:
        alerts.append({
            "category": "hazard",
            "severity": "HIGH",
            "message": f"{len(hazards)} road hazards reported. Deploying maintenance priority notifications.",
            "is_active": True
        })
        
    # Crowd Density
    if crowd:
        alerts.append({
            "category": "crowd",
            "severity": "MEDIUM",
            "message": "Crowd density increasing in commercial sectors. Advising reroute for emergency vehicles.",
            "is_active": True
        })
        
    # Parking Insights
    high_occ_parks = [p for p in parking if p.get("occupancy_percent", 0) > 90]
    if high_occ_parks:
        park_name = high_occ_parks[0]["name"]
        alerts.append({
            "category": "parking",
            "severity": "MEDIUM",
            "message": f"Parking occupancy exceeds 90% in {park_name}. Redirecting incoming traffic to alternates.",
            "is_active": True
        })
        
    # Transport Insights
    delayed_transport = [t for t in transport if t.get("status") == "DELAYED"]
    if len(delayed_transport) > 3:
        alerts.append({
            "category": "transport",
            "severity": "LOW",
            "message": "Multiple public transport routes experiencing delays. Updating ETA forecasts.",
            "is_active": True
        })
        
    if metrics.get("sos_requests", 0) > 0:
        alerts.append({
            "category": "emergency",
            "severity": "CRITICAL",
            "message": f"Live SOS requests active ({metrics['sos_requests']}). Dispatching nearest emergency units.",
            "is_active": True
        })
        
    # Ensure at least some mock insights if everything is quiet
    if not alerts:
        alerts.append({
            "category": "system",
            "severity": "LOW",
            "message": "City conditions are stable. AI monitoring active across all zones.",
            "is_active": True
        })
        
    dr.save_city_alerts(alerts)
    return alerts
