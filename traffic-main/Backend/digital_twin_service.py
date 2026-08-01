import city_metrics_service as cms
import city_prediction_service as cps
import city_dashboard_service as cds
import dashboard_repository as dr

# Existing services to pull overlay data
import traffic_repository as tr
import weather_repository as wr
import crowd_repository as cr
import hazard_service as hs
import live_data_service as ld

def get_full_dashboard_snapshot() -> dict:
    """Orchestrates all data sources to provide a unified Smart City Digital Twin view."""
    
    # 1. Fetch overlay data
    traffic_reports = tr.get_live_reports()
    hazards = hs.get_active_hazards_enriched()
    crowd = cr.get_crowd_reports()
    transport = dr.get_transport_status()
    parking = dr.get_parking_status()
    
    # 2. Calculate current KPIs
    metrics = cms.calculate_current_metrics()
    
    # 3. Generate Predictions
    predictions = cps.generate_predictions(metrics)
    
    # 4. Generate AI Insights & Alerts
    insights = cds.generate_ai_insights(metrics, transport, parking, hazards, crowd)
    
    snapshot = {
        "status": "online",
        "metrics": metrics,
        "predictions": predictions,
        "insights": insights,
        "layers": {
            "traffic": traffic_reports,
            "hazards": hazards,
            "crowd": crowd,
            "transport": transport,
            "parking": parking,
            "emergency": hs.get_active_hazards_enriched()
        }
    }
    
    # NOTE: Supabase realtime broadcast requires the async client and is handled
    # by the frontend polling this REST endpoint directly. The frontend JS sets up
    # its own realtime subscription via the Supabase JS SDK.
    return snapshot
