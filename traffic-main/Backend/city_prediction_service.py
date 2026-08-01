import random
import dashboard_repository as dr

def generate_predictions(current_metrics: dict) -> list:
    """Generates AI predictions for 15, 30, and 60 minutes based on current metrics."""
    horizons = [15, 30, 60]
    predictions = []
    
    for h in horizons:
        # Simulate an ML model forecasting by slightly perturbing current values
        # The further out the horizon, the larger the variance and lower the confidence
        variance = (h / 100.0) * 2.0  # Increased variance: 0.30, 0.60, 1.20
        
        # Traffic typically worsens during peak, we'll randomly adjust it
        pred_traffic = current_metrics.get("traffic_index", 50) * (1 + random.uniform(-variance, variance))
        pred_traffic = min(100.0, max(0.0, pred_traffic))
        
        pred_weather = current_metrics.get("weather_severity_index", 0) * (1 + random.uniform(-variance/2, variance))
        pred_weather = min(100.0, max(0.0, pred_weather))
        
        pred_crowd = current_metrics.get("crowd_density_index", 30) * (1 + random.uniform(-variance, variance))
        pred_crowd = min(100.0, max(0.0, pred_crowd))
        
        pred_parking = current_metrics.get("parking_occupancy", 50) + random.uniform(-10*variance, 20*variance)
        pred_parking = min(100.0, max(0.0, pred_parking))
        
        confidence = 1.0 - (h / 120.0) - random.uniform(0.0, 0.1) # 15m is ~80%, 60m is ~40%
        
        pred = {
            "time_horizon": h,
            "predicted_traffic_index": round(pred_traffic, 1),
            "predicted_crime_risk": round(random.uniform(10, 40) * (1 + random.uniform(-variance, variance)), 1),
            "predicted_weather_severity": round(pred_weather, 1),
            "predicted_parking_occupancy": round(pred_parking, 1),
            "predicted_crowd_density": round(pred_crowd, 1),
            "predicted_hazard_risk": round(random.uniform(5, 20) * (1 + random.uniform(0, variance)), 1),
            "predicted_emergency_load": round(random.uniform(20, 80) * (1 + random.uniform(-variance, variance)), 1),
            "predicted_transport_congestion": round(random.uniform(40, 90) * (1 + random.uniform(-variance, variance)), 1),
            "confidence_score": round(confidence, 2)
        }
        
        import city_manager as cm
        active = cm.current()
        city_key = active.city_key if active else "bengaluru"

        if h == 15:
            if city_key == "bengaluru":
                pred["ai_forecast_summary"] = random.choice([
                    "Traffic build-up expected near Majestic; minor delays in Purple Line.",
                    "Stable conditions ahead. Short-term congestion near MG Road.",
                    "Weather clearing. Fast traffic flow expected across major arterial roads.",
                    "Sudden spike in cab demand near Indiranagar detected. Expect slow movement."
                ])
            else:
                pred["ai_forecast_summary"] = random.choice([
                    "Traffic build-up expected near Hitech City; minor delays in Metro.",
                    "Stable conditions ahead. Short-term congestion near Gachibowli.",
                    "Weather clearing. Fast traffic flow expected across major arterial roads.",
                    "Sudden spike in cab demand near Jubilee Hills detected. Expect slow movement."
                ])
        elif h == 30:
            if city_key == "bengaluru":
                pred["ai_forecast_summary"] = random.choice([
                    "Moderate rain predicted in South Bangalore. Expect 20% increase in cab demand.",
                    "Parking zones filling up at Indiranagar. Recommend rerouting traffic.",
                    "Gradual increase in crowd density at tech parks. Peak hour starting.",
                    "Potential bottleneck forming at Silk Board junction. Re-routing suggested."
                ])
            else:
                pred["ai_forecast_summary"] = random.choice([
                    "Moderate rain predicted in North Zone. Expect 20% increase in cab demand.",
                    "Parking zones filling up at Ameerpet. Recommend rerouting traffic.",
                    "Gradual increase in crowd density at tech parks. Peak hour starting.",
                    "Potential bottleneck forming at Raidurg junction. Re-routing suggested."
                ])
        else: # 60m
            if city_key == "bengaluru":
                pred["ai_forecast_summary"] = random.choice([
                    "Heavy congestion likely across Outer Ring Road. Deploy additional traffic units.",
                    "Significant shift in weather patterns. Ensure all emergency units are on standby.",
                    "Normalizing traffic conditions expected post-peak. Lower emergency load projected.",
                    "Widespread delays expected across all transit networks due to cascading effects."
                ])
            else:
                pred["ai_forecast_summary"] = random.choice([
                    "Heavy congestion likely across Outer Ring Road. Deploy additional traffic units.",
                    "Significant shift in weather patterns. Ensure all emergency units are on standby.",
                    "Normalizing traffic conditions expected post-peak. Lower emergency load projected.",
                    "Widespread delays expected across all transit networks due to cascading effects."
                ])

        predictions.append(pred)
        # Save only columns that exist in the DB schema (strip ai_forecast_summary)
        db_pred = {k: v for k, v in pred.items() if k != 'ai_forecast_summary'}
        dr.save_city_predictions(db_pred)
        
    return predictions
