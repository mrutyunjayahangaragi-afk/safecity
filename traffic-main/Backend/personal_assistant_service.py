import assistant_repository as ar
import journey_monitor
import assistant_recommendation_engine as are
import assistant_alert_engine as aae

def start_assistant(user_id, lat, lng):
    session_id = ar.create_session(user_id, lat, lng)
    return {
        "greeting": "Hello! I am your AI Personal Safety Assistant. I am now monitoring your journey.",
        "session_id": session_id
    }

def process_ping(session_id, user_id, lat, lng, speed, context_overrides: dict):
    # 1. Calculates current safety score (mocking city_metrics_service)
    safety_score = 85 

    # 2. Logs telemetry via ar.log_telemetry
    ar.log_telemetry(session_id, user_id, lat, lng, speed)

    # 3. Analyzes for anomalies via journey_monitor
    detected_events = journey_monitor.analyze_anomalies(session_id, lat, lng, speed, context_overrides)

    # 4. Generates recommendations via are.generate_recommendations
    recommendations = are.generate_recommendations(session_id, safety_score, detected_events)

    # 5. Returns dict with status, safety_score, recommendations, detected_events, requires_checkin
    requires_checkin = False
    if detected_events:
        for event in detected_events:
            if isinstance(event, dict) and event.get("severity") == "high":
                requires_checkin = True
                break

    return {
        "status": "active",
        "safety_score": safety_score,
        "recommendations": recommendations,
        "detected_events": detected_events,
        "requires_checkin": requires_checkin
    }

def handle_checkin(session_id, status):
    ar.update_checkin_response(session_id, status)
    return {"status": "success", "message": "Check-in recorded"}

def stop_assistant(session_id):
    ar.end_session(session_id)
    return {"status": "stopped", "message": "Assistant stopped successfully"}
