import sys

new_code = """
# AI Personal Safety Assistant Routes
from pydantic import BaseModel
from typing import Optional
try:
    import personal_assistant_service as pas
except ImportError:
    pass

class AssistantStartReq(BaseModel):
    user_id: str
    lat: float
    lng: float

class AssistantPingReq(BaseModel):
    session_id: str
    user_id: str
    lat: float
    lng: float
    speed: float = 0.0
    context_overrides: Optional[dict] = {}

class AssistantCheckinReq(BaseModel):
    session_id: str
    status: str

@app.post("/assistant/start", tags=["Assistant"])
def start_assistant(req: AssistantStartReq):
    try:
        return pas.start_assistant(req.user_id, req.lat, req.lng)
    except Exception as e:
        return {"error": str(e)}

@app.post("/assistant/ping", tags=["Assistant"])
def ping_assistant(req: AssistantPingReq):
    try:
        return pas.process_ping(req.session_id, req.user_id, req.lat, req.lng, req.speed, req.context_overrides)
    except Exception as e:
        return {"error": str(e)}

@app.post("/assistant/checkin", tags=["Assistant"])
def checkin_assistant(req: AssistantCheckinReq):
    try:
        return pas.handle_checkin(req.session_id, req.status)
    except Exception as e:
        return {"error": str(e)}

@app.post("/assistant/stop", tags=["Assistant"])
def stop_assistant(session_id: str):
    try:
        return pas.stop_assistant(session_id)
    except Exception as e:
        return {"error": str(e)}
"""

with open('c:/safe/traffic-main/Backend/app.py', 'a', encoding='utf-8') as f:
    f.write(new_code)

print("Appended routes successfully.")
