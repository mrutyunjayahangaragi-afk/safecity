import os
import json
import uuid
from datetime import datetime, timezone

USE_SUPABASE = os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY")
if USE_SUPABASE:
    from supabase import create_client, Client
    supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    # Use service key for writes (bypasses RLS). Fall back to anon client if not set.
    _service_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    _write_client: Client = create_client(os.getenv("SUPABASE_URL"), _service_key)
else:
    supabase = None
    _write_client = None

# Fallbacks
_sessions = {}
_telemetry = []
_recommendations = []
_events = []
_checkins = []
_alerts = []


def create_session(user_id, lat, lng):
    session_id = str(uuid.uuid4())
    data = {
        "id": session_id,
        "user_id": user_id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "start_lat": lat,
        "start_lng": lng,
        "is_active": True
    }
    if _write_client:
        try:
            _write_client.table("assistant_sessions").insert(data).execute()
        except Exception as e:
            print(f"DB Error (create_session): {e}")
    else:
        _sessions[session_id] = data
    return session_id


def end_session(session_id):
    if _write_client:
        try:
            _write_client.table("assistant_sessions").update({
                "end_time": datetime.now(timezone.utc).isoformat(),
                "is_active": False
            }).eq("id", session_id).execute()
        except Exception as e:
            print(f"DB Error (end_session): {e}")
    else:
        if session_id in _sessions:
            _sessions[session_id]["end_time"] = datetime.now(timezone.utc).isoformat()
            _sessions[session_id]["is_active"] = False


def log_telemetry(session_id, lat, lng, speed, safety_score, context):
    data = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": lat,
        "longitude": lng,
        "speed": speed,
        "safety_score": safety_score,
        "context_data": context
    }
    if _write_client:
        try:
            _write_client.table("journey_monitoring").insert(data).execute()
        except Exception as e:
            print(f"DB Error (log_telemetry): {e}")
    else:
        _telemetry.append(data)


def save_recommendation(session_id, text, trigger, confidence):
    data = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendation_text": text,
        "trigger_condition": trigger,
        "confidence_score": confidence
    }
    if _write_client:
        try:
            _write_client.table("assistant_recommendations").insert(data).execute()
        except Exception as e:
            print(f"DB Error (save_recommendation): {e}")
    else:
        _recommendations.append(data)


def save_event(session_id, event_type, description, severity):
    data = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "description": description,
        "severity": severity
    }
    if _write_client:
        try:
            _write_client.table("assistant_events").insert(data).execute()
        except Exception as e:
            print(f"DB Error (save_event): {e}")
    else:
        _events.append(data)


def log_checkin_prompt(session_id):
    checkin_id = str(uuid.uuid4())
    data = {
        "id": checkin_id,
        "session_id": session_id,
        "prompt_time": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    if _write_client:
        try:
            _write_client.table("journey_checkins").insert(data).execute()
        except Exception as e:
            print(f"DB Error (log_checkin_prompt): {e}")
    else:
        _checkins.append(data)
    return checkin_id


def update_checkin_response(checkin_id, status):
    if _write_client:
        try:
            _write_client.table("journey_checkins").update({
                "response_time": datetime.now(timezone.utc).isoformat(),
                "status": status
            }).eq("id", checkin_id).execute()
        except Exception as e:
            print(f"DB Error (update_checkin_response): {e}")
    else:
        for c in _checkins:
            if c["id"] == checkin_id:
                c["response_time"] = datetime.now(timezone.utc).isoformat()
                c["status"] = status
                break


def save_alert(session_id, alert_type, payload):
    data = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_type": alert_type,
        "payload": payload
    }
    if _write_client:
        try:
            _write_client.table("assistant_alerts").insert(data).execute()
        except Exception as e:
            print(f"DB Error (save_alert): {e}")
    else:
        _alerts.append(data)
