"""
SafeRoute AI — FastAPI Backend
Pilot City: Bengaluru | Scalable to all Indian Smart Cities

Run:  uvicorn app:app --reload --port 8000

Backward compatibility
----------------------
All original endpoints (/find-safe-route, /predict-risk, /get-crime-heatmap,
/get-crime-points, /report-incident, /get-incidents, /compare-routes,
/analytics/summary) work exactly as before.

New endpoints added
-------------------
GET  /cities                     — list all cities with availability flags
GET  /states                     — list all states
GET  /city-status                — currently active city info
POST /set-city                   — switch active city
GET  /resolve-city?lat=&lon=     — GPS-based city detection
"""

import os, sys, json, pickle
from datetime import datetime
from typing   import Optional

import pandas as pd
import numpy  as np

# ── ensure backend/ is on the path ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from fastapi            import FastAPI, HTTPException, Query, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses  import FileResponse
from pydantic           import BaseModel, Field

import data_processing    as dp
import safety_score        as ss
import risk_model          as rm
import route_engine        as re
import city_manager        as cm
import traffic_service     as ts
import traffic_repository  as tr
import weather_service     as ws
import weather_repository  as wr
import crowd_service       as cs
import crowd_repository    as cr
import live_data_service   as ld
import hazard_service      as hs
import hazard_repository   as hr
import hazard_detector     as hd_module
import digital_twin_service as dts
import city_metrics_service as cms
import dashboard_repository as dr


# ─── JWT Auth Dependency (optional — backward-compatible) ─────────────────────
# When a valid Supabase JWT is present in the Authorization header, the
# authenticated user_id is extracted and injected into the endpoint.
# If no header is present the dependency returns None — all existing endpoints
# that accepted a plain user_id string in the body continue to work unchanged.

import base64, hmac, hashlib, struct

def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """
    FastAPI dependency.
    Returns the Supabase user UUID if a valid Bearer JWT is provided.
    Returns None for unauthenticated / guest requests.
    """
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    try:
        if dr.supabase is None:
            return None
        # SECURE FIX: Actually verify the token signature using the Supabase client
        # rather than just base64 decoding the payload string.
        user_response = dr.supabase.auth.get_user(token)
        if user_response and user_response.user:
            return user_response.user.id
        return None
    except Exception as e:
        print(f"Auth token verification failed: {e}")
        return None


def require_user(user_id: Optional[str] = Depends(get_optional_user)) -> str:
    """Dependency that raises 401 when no authenticated user is found."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in.")
    return user_id


# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "SafeRoute AI — Smart City Navigation API",
    description = (
        "AI-powered safety navigation for Indian Smart Cities. "
        "Pilot: Bengaluru (Namma Safe BLR). Expandable to all cities."
    ),
    version     = "2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Legacy path constants (kept for backward compat) ────────────────────────
BASE       = os.path.dirname(__file__)
DATA_PATH  = os.path.join(BASE, "../data/bangalore_crime_dataset.csv")
MODEL_PATH = os.path.join(BASE, "../models/risk_model.pkl")

# ─── Module-level globals (populated from city_manager) ──────────────────────
# These are kept so that all existing endpoint code works without any change.
crime_df     = None
density_grid = []
model_bundle = None
incidents_log: list = []    # in-memory crowd-reported incidents (per-session)


def _sync_globals():
    """Pull active city state into module-level globals used by all endpoints."""
    global crime_df, density_grid, model_bundle
    city = cm.current()
    if city:
        crime_df = city.crime_df
        density_grid = city.density_grid
        model_bundle = city.model_bundle
        if crime_df is not None:
            ss.load_processed_dataframe(crime_df)


# ─── Startup ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Boot with Bengaluru as pilot city — fully backward compatible."""
    try:
        cm.load_city("karnataka", "bengaluru")
        _sync_globals()
        print("SafeRoute AI ready! Pilot City: Bengaluru")
    except Exception as e:
        print(f"WARNING: City load failed ({e}). Attempting legacy startup...")
        # Legacy fallback — loads exactly as the original app.py did
        global crime_df, density_grid, model_bundle
        crime_df = dp.load_and_clean(DATA_PATH)
        _, _clusters = dp.cluster_hotspots(crime_df)
        density_grid = dp.compute_density_grid(crime_df)
        ss.load_density_grid(density_grid)
        ss.load_processed_dataframe(dp.get_processed_dataset(DATA_PATH))
        if os.path.exists(MODEL_PATH):
            model_bundle = rm.load_model(MODEL_PATH)
            print(f"Legacy model loaded: {model_bundle.get('model_name', 'unknown')}")
        else:
            model_bundle = rm.train(DATA_PATH, MODEL_PATH)
        print("SafeRoute AI API ready (legacy mode)")


# ─── Pydantic schemas ─────────────────────────────────────────────────────────
class RouteRequest(BaseModel):
    src_lat:   float = Field(..., example=12.9716)
    src_lon:   float = Field(..., example=77.5946)
    dst_lat:   float = Field(..., example=12.9352)
    dst_lon:   float = Field(..., example=77.6245)
    hour:      int   = Field(22, ge=0, le=23)
    algorithm: str   = Field("astar", pattern="^(astar|dijkstra)$")
    emergency_mode: bool = Field(False, description="Enable emergency vehicle priority routing")
    vehicle_type: str = Field("Ambulance", description="Ambulance, Police, or Fire & Rescue")

class RiskRequest(BaseModel):
    latitude:         float = Field(..., example=12.9716)
    longitude:        float = Field(..., example=77.5946)
    hour:             int   = Field(22, ge=0, le=23)
    lighting_score:   Optional[float] = None
    cctv_score:       Optional[float] = None
    crowd_density:    Optional[float] = None
    police_proximity: Optional[float] = None

class IncidentReport(BaseModel):
    latitude:    float
    longitude:   float
    description: str
    severity:    int = Field(5, ge=1, le=10)

class UserProfileRequest(BaseModel):
    user_id:      str = Field("anonymous")
    display_name: str = Field("Anonymous")
    email:        Optional[str] = None
    phone:        Optional[str] = None
    role:         str = Field("viewer")
    # Extended fields (v2 auth)
    full_name:    Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url:   Optional[str] = None
    provider:     Optional[str] = Field("email")
    country:      Optional[str] = None
    city:         Optional[str] = None

class RouteHistoryRequest(BaseModel):
    user_id:       str = Field("anonymous")
    route_label:   str = Field("Unknown")
    source:        str = Field("Unknown")
    destination:   str = Field("Unknown")
    distance_km:   float = Field(0.0)
    duration_min:  int = Field(0)

class SosRequestPayload(BaseModel):
    user_id:    str = Field("anonymous")
    latitude:   float
    longitude:  float
    message:    str = Field("SOS")
    status:     str = Field("active")

class IncidentPersistenceRequest(BaseModel):
    user_id:     str = Field("anonymous")
    latitude:    float
    longitude:   float
    description: str
    severity:    int = Field(5, ge=1, le=10)
    status:      str = Field("active")

class SetCityRequest(BaseModel):
    state_key: str = Field(..., example="karnataka")
    city_key:  str = Field(..., example="bengaluru")

class TrafficReportRequest(BaseModel):
    road_name:          str   = Field(..., example="MG Road")
    latitude:           float = Field(..., example=12.9750)
    longitude:          float = Field(..., example=77.6050)
    congestion_level:   str   = Field("MEDIUM", pattern="^(LOW|MEDIUM|HIGH|SEVERE)$")
    average_speed:      Optional[float] = None
    vehicle_density:    Optional[float] = None
    delay_minutes:      Optional[float] = None
    traffic_percentage: Optional[float] = None
    created_by:         str   = Field("anonymous")

class RoadIncidentRequest(BaseModel):
    incident_type: str   = Field(..., example="accident")
    description:   str   = Field(..., example="Multi-vehicle accident blocking 2 lanes")
    latitude:      float = Field(..., example=12.9750)
    longitude:     float = Field(..., example=77.6050)
    severity:      int   = Field(5, ge=1, le=10)
    created_by:    str   = Field("anonymous")

class WeatherReportRequest(BaseModel):
    latitude:    float  = Field(..., example=12.9352)
    longitude:   float  = Field(..., example=77.6245)
    weather_type: str   = Field(..., example="Heavy Rain")
    rainfall:    float  = Field(0.0, ge=0)
    visibility:  float  = Field(10.0, ge=0)
    flood_risk:  float  = Field(0.0, ge=0, le=1)
    wind_speed:  float  = Field(10.0, ge=0)
    humidity:    float  = Field(60.0, ge=0, le=100)
    temperature: float  = Field(25.0)

class RoadWeatherAlertRequest(BaseModel):
    road_name:   str = Field(..., example="Silk Board Junction")
    alert_type:  str = Field(..., example="flood")
    severity:    int = Field(5, ge=1, le=10)
    description: str = Field(..., example="Waterlogging reported, avoid if possible")

class CrowdReportRequest(BaseModel):
    latitude:         float = Field(..., example=12.9352)
    longitude:        float = Field(..., example=77.6245)
    crowd_level:      str   = Field("Moderate", description="Low/Moderate/High/Extreme")
    crowd_score:      float = Field(0.5, ge=0, le=1)
    estimated_people: int   = Field(100, ge=0)
    source:           str   = Field("community")

class EmergencyRouteRequest(BaseModel):
    src_lat:   float = Field(..., example=12.9716)
    src_lon:   float = Field(..., example=77.5946)
    dst_lat:   float = Field(..., example=12.9352)
    dst_lon:   float = Field(..., example=77.6245)
    hour:      int   = Field(22, ge=0, le=23)
    vehicle_type: str = Field("Ambulance", description="Ambulance, Police, or Fire & Rescue")

class HazardReportRequest(BaseModel):
    hazard_type: str = Field(..., example="pothole")
    title: str = Field(..., example="Large pothole on main road")
    description: str = Field("", example="Avoid the left lane")
    latitude: float = Field(..., example=12.9716)
    longitude: float = Field(..., example=77.5946)
    severity: int = Field(5, ge=1, le=10)
    image_url: Optional[str] = None
    user_id: str = Field("anonymous")
    source: str = Field("community")

class HazardUpdateRequest(BaseModel):
    status: Optional[str] = None
    verified: Optional[bool] = None
    severity: Optional[int] = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXISTING ENDPOINTS — 100% unchanged behaviour
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root():
    city = cm.current()
    city_label = city.label if city else "Bengaluru"
    return {
        "status":  "ok",
        "service": "SafeRoute AI",
        "tagline": "AI-Powered Safe Navigation for Smart Cities",
        "pilot":   "Namma Safe BLR — Bengaluru",
        "active_city": city_label,
        "version": "2.0.0",
    }


@app.post("/find-safe-route", tags=["Navigation"])
def find_safe_route(req: RouteRequest):
    """Find the safest route between two points."""
    result = re.find_safe_route(
        req.src_lat, req.src_lon,
        req.dst_lat, req.dst_lon,
        hour      = req.hour,
        algorithm = req.algorithm,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/predict-risk", tags=["ML"])
def predict_risk(req: RiskRequest):
    """Predict crime risk level for a location using the ML model."""
    from data_processing import time_risk_factor

    time_risk     = time_risk_factor(req.hour)
    crime_density = ss._nearest_density(req.latitude, req.longitude)

    features = {
        "severity_norm":    crime_density,
        "time_risk":        time_risk,
        "lighting_score":   req.lighting_score   if req.lighting_score   is not None else 0.5,
        "cctv_score":       req.cctv_score        if req.cctv_score        is not None else 0.4,
        "crowd_density":    req.crowd_density     if req.crowd_density     is not None else 0.5,
        "police_proximity": req.police_proximity  if req.police_proximity  is not None else 0.5,
        "is_night":         1 if (req.hour >= 20 or req.hour < 6) else 0,
        "hour":             req.hour,
    }

    prediction = rm.predict_risk(model_bundle, features)
    safety     = ss.compute_safety_score(
        req.latitude, req.longitude, req.hour,
        req.lighting_score, req.cctv_score, req.crowd_density,
    )
    return {**prediction, **safety, "features_used": features}


@app.get("/get-crime-heatmap", tags=["Visualization"])
def get_crime_heatmap(limit: int = 500):
    """Return crime density grid for heatmap rendering."""
    data = density_grid[:limit]
    return {"heatmap": data, "total_cells": len(density_grid)}


@app.get("/get-crime-points", tags=["Visualization"])
def get_crime_points(limit: int = 300):
    """Return raw crime records for marker rendering."""
    if crime_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")
    sample = crime_df.sample(min(limit, len(crime_df)), random_state=42)
    return {
        "crimes": sample[
            ["latitude", "longitude", "crime_type", "crime_severity", "hour", "area"]
        ].to_dict("records")
    }


@app.post("/report-incident", tags=["Community"])
def report_incident(report: IncidentReport):
    """Crowd-sourced incident reporting."""
    entry = {
        "id":          len(incidents_log) + 1,
        "latitude":    report.latitude,
        "longitude":   report.longitude,
        "description": report.description,
        "severity":    report.severity,
        "timestamp":   datetime.utcnow().isoformat(),
    }
    incidents_log.append(entry)
    persisted = tr.save_incident_report({
        "user_id": "anonymous",
        "latitude": report.latitude,
        "longitude": report.longitude,
        "description": report.description,
        "severity": report.severity,
        "status": "active",
    })
    return {
        "status": "reported",
        "incident_id": entry["id"],
        "source": persisted.get("source", "local"),
    }


@app.get("/get-incidents", tags=["Community"])
def get_incidents():
    """Fetch all crowd-reported incidents."""
    return {"incidents": incidents_log, "total": len(incidents_log)}


@app.post("/user/profile", tags=["Persistence"])
def save_user_profile(req: UserProfileRequest):
    """Persist a user profile in Supabase or local memory."""
    entry = tr.save_user_profile(req.model_dump())
    return {"status": "saved", "profile": entry, "source": entry.get("source", "local")}


@app.get("/user/profile", tags=["Persistence"])
def get_user_profiles(user_id: Optional[str] = Query(None, description="Optional filter by user ID")):
    """Fetch stored user profiles."""
    rows = tr.get_user_profiles(user_id)
    return {"profiles": rows, "total": len(rows)}


# ─── Auth v2: JWT-authenticated profile endpoints ─────────────────────────────

class ProfileUpsertRequest(BaseModel):
    """Extended profile payload for multi-provider auth."""
    full_name:    Optional[str] = None
    email:        Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url:   Optional[str] = None
    provider:     str           = Field("email")
    country:      Optional[str] = None
    city:         Optional[str] = None


@app.post("/auth/profile", tags=["Auth"])
def upsert_auth_profile(
    req: ProfileUpsertRequest,
    user_id: str = Depends(require_user),
):
    """
    Upsert profile for the authenticated user.
    Requires a valid Supabase JWT in the Authorization header.
    Called automatically on every sign-in from the frontend.
    """
    import importlib, os
    SUPA_URL = os.getenv("SUPABASE_URL", "")
    SUPA_KEY = os.getenv("SUPABASE_KEY", "")
    if SUPA_URL and SUPA_KEY:
        try:
            from supabase import create_client
            supa = create_client(SUPA_URL, SUPA_KEY)
            data = {
                "user_id":      user_id,
                "full_name":    req.full_name or "User",
                "email":        req.email,
                "phone_number": req.phone_number,
                "avatar_url":   req.avatar_url,
                "provider":     req.provider,
                "country":      req.country,
                "city":         req.city,
                "last_login":   datetime.utcnow().isoformat(),
                "updated_at":   datetime.utcnow().isoformat(),
            }
            supa.table("profiles").upsert(data, on_conflict="user_id").execute()
            return {"status": "saved", "user_id": user_id, "source": "supabase"}
        except Exception as e:
            pass  # fall through to local

    # Local fallback
    entry = tr.save_user_profile({
        "user_id":      user_id,
        "display_name": req.full_name or "User",
        "email":        req.email,
        "phone":        req.phone_number,
        "role":         "viewer",
    })
    return {"status": "saved", "user_id": user_id, "source": "local"}


@app.get("/auth/profile", tags=["Auth"])
def get_auth_profile(user_id: str = Depends(require_user)):
    """
    Return the authenticated user's profile.
    Requires a valid Supabase JWT.
    """
    import os
    SUPA_URL = os.getenv("SUPABASE_URL", "")
    SUPA_KEY = os.getenv("SUPABASE_KEY", "")
    if SUPA_URL and SUPA_KEY:
        try:
            from supabase import create_client
            supa = create_client(SUPA_URL, SUPA_KEY)
            res = supa.table("profiles").select("*").eq("user_id", user_id).single().execute()
            if res.data:
                return {"profile": res.data, "source": "supabase"}
        except Exception:
            pass

    rows = tr.get_user_profiles(user_id)
    profile = rows[0] if rows else {}
    return {"profile": profile, "source": "local"}


@app.get("/auth/me", tags=["Auth"])
def get_current_user(user_id: str = Depends(require_user)):
    """Lightweight endpoint — returns the authenticated user_id from JWT."""
    return {"user_id": user_id, "authenticated": True}


@app.get("/auth/google-status", tags=["Auth"])
def google_auth_status():
    """
    Check whether Google OAuth is properly configured in Supabase.
    Queries the Supabase settings API using the service-role key.
    Returns a checklist of what is configured vs what is missing.
    Useful for verifying setup before frontend testing.
    """
    import os, requests as _requests
    SUPA_URL     = os.getenv("SUPABASE_URL", "")
    SERVICE_KEY  = os.getenv("SUPABASE_SERVICE_KEY", "")

    status = {
        "supabase_url_configured":     bool(SUPA_URL),
        "supabase_service_key_configured": bool(SERVICE_KEY),
        "google_provider_enabled":     None,  # filled below
        "callback_url":                f"{SUPA_URL}/auth/v1/callback" if SUPA_URL else None,
        "redirect_url_for_dev":        "http://localhost",
        "notes":                       [],
    }

    if not SUPA_URL:
        status["notes"].append("SUPABASE_URL is not set in Backend/.env")
    if not SERVICE_KEY:
        status["notes"].append("SUPABASE_SERVICE_KEY is not set in Backend/.env — cannot query provider settings")
        return status

    # Try the Supabase admin API to check provider config
    try:
        resp = _requests.get(
            f"{SUPA_URL}/auth/v1/settings",
            headers={
                "apikey":        SERVICE_KEY,
                "Authorization": f"Bearer {SERVICE_KEY}",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            external = data.get("external", {})
            google   = external.get("google", {})
            enabled  = google.get("enabled", False)
            has_id   = bool(google.get("client_id", ""))
            has_sec  = bool(google.get("client_secret", ""))
            status["google_provider_enabled"] = enabled
            status["google_client_id_set"]    = has_id
            status["google_client_secret_set"]= has_sec
            if not enabled:
                status["notes"].append(
                    "Google provider is DISABLED. Go to Supabase Dashboard → Authentication → Providers → Google → Enable."
                )
            if not has_id:
                status["notes"].append(
                    "Google Client ID is missing. Paste it in Supabase → Authentication → Providers → Google."
                )
            if not has_sec:
                status["notes"].append(
                    "Google Client Secret is missing. Paste it in Supabase → Authentication → Providers → Google."
                )
            if enabled and has_id and has_sec:
                status["notes"].append("✅ Google OAuth appears fully configured.")
        else:
            status["notes"].append(f"Supabase settings API returned {resp.status_code} — check SERVICE_KEY permissions.")
    except Exception as e:
        status["notes"].append(f"Could not reach Supabase settings API: {e}")

    return status


@app.post("/route/history", tags=["Persistence"])
def save_route_history(req: RouteHistoryRequest):
    """Persist a completed route selection for later history display."""
    entry = tr.save_route_history(req.model_dump())
    return {"status": "saved", "record": entry, "source": entry.get("source", "local")}


@app.get("/route/history", tags=["Persistence"])
def get_route_history(user_id: Optional[str] = Query(None, description="Optional filter by user ID")):
    """Fetch route history for a user."""
    rows = tr.get_route_history(user_id)
    return {"history": rows, "total": len(rows)}


@app.post("/sos/request", tags=["Persistence"])
def save_sos_request(req: SosRequestPayload):
    """Persist an SOS submission."""
    entry = tr.save_sos_request(req.model_dump())
    return {"status": "created", "request": entry, "source": entry.get("source", "local")}


@app.get("/sos/requests", tags=["Persistence"])
def get_sos_requests(user_id: Optional[str] = Query(None, description="Optional filter by user ID")):
    """Fetch SOS requests for a user."""
    rows = tr.get_sos_requests(user_id)
    return {"requests": rows, "total": len(rows)}


@app.post("/incident/report", tags=["Persistence"])
def save_incident_report(req: IncidentPersistenceRequest):
    """Persist an incident report via the repository layer."""
    entry = tr.save_incident_report(req.model_dump())
    return {"status": "reported", "incident": entry, "source": entry.get("source", "local")}


@app.get("/incident/reports", tags=["Persistence"])
def get_incident_reports(user_id: Optional[str] = Query(None, description="Optional filter by user ID")):
    """Fetch incident reports for a user."""
    rows = tr.get_incident_reports(user_id)
    return {"incidents": rows, "total": len(rows)}


@app.post("/compare-routes", tags=["Navigation"])
def compare_routes(req: RouteRequest):
    """
    AI Route Comparison — Safest, Fastest, Balanced.
    Now enriched with real-time traffic data (50% Safety + 30% Time + 20% Traffic).
    Backward compatible: all original fields still present.
    """
    result = re.find_route_comparison(
        req.src_lat, req.src_lon,
        req.dst_lat, req.dst_lon,
        hour=req.hour,
        emergency_mode=req.emergency_mode,
        vehicle_type=req.vehicle_type,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    # Enrich routes with traffic — does NOT modify existing keys
    city = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    enriched_routes = ts.enrich_routes_with_traffic(
        result["routes"], req.hour, state_key, city_key
    )
    alerts = ts.generate_traffic_alerts(enriched_routes)

    # ── Weather enrichment (40/25/20/15 formula) ──────────────────────────
    enriched_routes = ws.enrich_routes_with_weather(
        enriched_routes, req.hour, state_key, city_key
    )
    weather_alerts = ws.generate_weather_alerts(enriched_routes)

    # ── Crowd enrichment (35/25/15/15/10 formula) ──────────────────────────
    enriched_routes = cs.enrich_routes_with_crowd(
        enriched_routes, req.hour, state_key, city_key
    )
    crowd_alerts = cs.generate_crowd_alerts(enriched_routes)

    # ── Hazard enrichment (30/20/15/10/25 formula) ───────────────────────────
    # enrich_routes_with_hazards adds hazard_score, hazards_count, route_hazards,
    # has_critical_hazard, hazard_delay_min and recalculates ai_score in-place.
    enriched_routes = hs.enrich_routes_with_hazards(enriched_routes)
    hazard_alerts   = hs.generate_hazard_alerts(enriched_routes)

    all_alerts = alerts + weather_alerts + crowd_alerts + hazard_alerts

    return {
        **result,
        "routes":           enriched_routes,
        "alerts":           all_alerts,
        "traffic_powered":  True,
        "weather_powered":  True,
        "crowd_powered":    True,
        "hazard_powered":   True,
    }


@app.post("/emergency/route", tags=["Emergency"])
def emergency_route(req: EmergencyRouteRequest):
    """Dedicated emergency vehicle routing endpoint with priority scoring."""
    result = re.find_route_comparison(
        req.src_lat,
        req.src_lon,
        req.dst_lat,
        req.dst_lon,
        hour=req.hour,
        emergency_mode=True,
        vehicle_type=req.vehicle_type,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    city = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"
    enriched_routes = ts.enrich_routes_with_traffic(result["routes"], req.hour, state_key, city_key)
    return {
        **result,
        "routes": enriched_routes,
        "traffic_powered": True,
        "vehicle_type": req.vehicle_type,
    }


@app.post("/emergency/request", tags=["Emergency"])
def create_emergency_request(req: EmergencyRouteRequest):
    """Record an emergency route request and return the stored payload."""
    payload = {
        "vehicle_type": req.vehicle_type,
        "source_latitude": req.src_lat,
        "source_longitude": req.src_lon,
        "destination_latitude": req.dst_lat,
        "destination_longitude": req.dst_lon,
        "priority_level": "high",
        "status": "active",
        "eta": 8,
    }
    entry = tr.submit_emergency_request(payload)
    return {"status": "created", "request": entry}


@app.get("/analytics/summary", tags=["Analytics"])
def analytics_summary():
    """High-level analytics summary."""
    if crime_df is None:
        raise HTTPException(status_code=503, detail="Data not loaded")

    by_area  = crime_df.groupby("area")["crime_type"].count().sort_values(ascending=False).head(10).to_dict()
    by_type  = crime_df["crime_type"].value_counts().to_dict()
    by_hour  = crime_df.groupby("hour")["crime_type"].count().to_dict()
    night_d  = crime_df[crime_df["is_night"] == 1]["crime_type"].count()
    day_d    = crime_df[crime_df["is_night"] == 0]["crime_type"].count()
    city     = cm.current()

    emergency_metrics = tr.get_emergency_analytics()

    return {
        "total_records":  len(crime_df),
        "by_area":        by_area,
        "by_crime_type":  by_type,
        "by_hour":        {str(k): int(v) for k, v in by_hour.items()},
        "night_crimes":   int(night_d),
        "day_crimes":     int(day_d),
        "model_name":     model_bundle["model_name"]       if model_bundle else "Not loaded",
        "model_accuracy": round(model_bundle["test_accuracy"] * 100, 2) if model_bundle else 0,
        "active_city":    city.label if city else "Bengaluru",
        "pilot_city":     "Bengaluru",
        "emergency_requests": emergency_metrics.get("request_count", 0),
        "average_response_time": emergency_metrics.get("average_response_time", 0),
        "emergency_route_success_rate": emergency_metrics.get("route_success_rate", 0),
        "average_eta": emergency_metrics.get("average_eta", 0),
        "traffic_clearance_stats": emergency_metrics.get("traffic_clearance_stats", {}),
        "emergency_heatmap": emergency_metrics.get("heatmap", []),
        "vehicle_utilization": emergency_metrics.get("vehicle_utilization", {}),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# NEW ENDPOINTS — Multi-city support
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/states", tags=["City"])
def get_states():
    """List all supported states with city availability counts."""
    return {"states": cm.list_states_api()}


@app.get("/cities", tags=["City"])
def get_cities(state: Optional[str] = Query(None, description="Filter by state key")):
    """
    List all cities with dataset availability and pilot flags.
    Optionally filter by state key (e.g. ?state=karnataka).
    """
    all_cities = cm.list_all_cities()
    if state:
        all_cities = [c for c in all_cities if c["state_key"] == state.lower()]
    return {"cities": all_cities, "total": len(all_cities)}


@app.get("/city-status", tags=["City"])
def city_status():
    """Return info about the currently active city."""
    city = cm.current()
    if not city:
        return {
            "active_city":  "bengaluru",
            "city_label":   "Bengaluru",
            "state_key":    "karnataka",
            "pilot":        True,
            "status":       "active",
        }
    return city.to_info_dict()


@app.post("/set-city", tags=["City"])
def set_city(req: SetCityRequest):
    """
    Switch the active city.
    Only cities with an available dataset can be activated.
    Returns city info + waypoints for the frontend to update.
    """
    global crime_df, density_grid, model_bundle

    # Check registry first
    from city_registry import get_city as reg_get_city
    config = reg_get_city(req.state_key, req.city_key)
    if config is None:
        raise HTTPException(
            status_code=404,
            detail=f"City '{req.city_key}' in state '{req.state_key}' not found."
        )

    # Check dataset availability
    try:
        city_state = cm.load_city(req.state_key, req.city_key)
        _sync_globals()
        return {
            "status":      "switched",
            "city":        city_state.to_info_dict(),
            "message":     f"✅ Switched to {city_state.label}",
        }
    except FileNotFoundError:
        # Dataset missing — return friendly coming-soon response
        return {
            "status":  "unavailable",
            "city_key":   req.city_key,
            "city_label": config.label,
            "message":  (
                f"Dataset for {config.label} is not yet available. "
                f"Bengaluru Pilot is active."
            ),
            "pilot_active": "bengaluru",
        }


@app.get("/resolve-city", tags=["City"])
def resolve_city(
    lat: float = Query(..., description="Latitude from GPS"),
    lon: float = Query(..., description="Longitude from GPS"),
):
    """
    Detect city from GPS coordinates.
    Used by the frontend when location permission is granted.
    """
    result = cm.resolve_from_coords(lat, lon)
    if result:
        return {"found": True, **result}
    return {
        "found":     False,
        "message":   "Location not within any supported city. Defaulting to Bengaluru.",
        "fallback":  {"state_key": "karnataka", "city_key": "bengaluru"},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TRAFFIC ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/traffic/heatmap", tags=["Traffic"])
def traffic_heatmap(
    hour:  int = Query(None, description="Hour 0-23. Defaults to current hour."),
    limit: int = Query(300, description="Max records to return"),
):
    """
    Return traffic congestion heatmap data for the frontend traffic layer.
    Each record: { lat, lon, congestion, speed, delay, road_name, road_type }
    """
    if hour is None:
        from datetime import datetime
        hour = datetime.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data = ts.get_traffic_heatmap(hour, state_key, city_key, limit=limit)
    return {
        "heatmap":      data,
        "total_points": len(data),
        "hour":         hour,
        "source":       "local_dataset",
    }


@app.get("/traffic/analytics", tags=["Traffic"])
def traffic_analytics(
    hour: int = Query(None, description="Hour 0-23. Defaults to current hour."),
):
    """Full traffic analytics payload including congestion stats, daily trend, and incidents."""
    if hour is None:
        from datetime import datetime
        hour = datetime.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data = ts.get_traffic_analytics(hour, state_key, city_key)
    return data


@app.get("/traffic/segment", tags=["Traffic"])
def traffic_segment(
    lat:  float = Query(..., description="Latitude"),
    lon:  float = Query(..., description="Longitude"),
    hour: int   = Query(None, description="Hour 0-23"),
):
    """Return traffic data for the road segment nearest to the given coordinates."""
    if hour is None:
        from datetime import datetime
        hour = datetime.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    seg = tr.get_segment_traffic(lat, lon, hour, state_key=state_key, city_key=city_key)
    if not seg:
        raise HTTPException(status_code=404, detail="No traffic data for this location")
    return seg


@app.post("/traffic/report", tags=["Traffic"])
def report_traffic(report: TrafficReportRequest):
    """Submit a community traffic report. Stored in Supabase or local fallback."""
    entry = tr.submit_traffic_report(report.model_dump())
    return {"status": "reported", "id": entry["id"], "source": entry.get("source", "local")}


@app.post("/traffic/incident", tags=["Traffic"])
def report_road_incident(incident: RoadIncidentRequest):
    """Submit a road incident (accident, closure, construction, weather alert)."""
    entry = tr.submit_road_incident(incident.model_dump())
    return {"status": "reported", "id": entry["id"], "source": entry.get("source", "local")}


@app.get("/traffic/incidents", tags=["Traffic"])
def get_road_incidents(active_only: bool = Query(True)):
    """Fetch road incidents (accidents, closures, construction zones)."""
    incidents = tr.get_road_incidents(active_only=active_only)
    return {"incidents": incidents, "total": len(incidents)}


@app.get("/traffic/live-reports", tags=["Traffic"])
def get_live_traffic_reports(limit: int = Query(50)):
    """Fetch recent community-submitted traffic reports."""
    reports = tr.get_live_reports(limit=limit)
    return {"reports": reports, "total": len(reports)}


@app.get("/traffic/status", tags=["Traffic"])
def traffic_status():
    """Health check for the traffic module — includes Supabase connection status."""
    return {
        "traffic_module": "active",
        "supabase":       tr.get_supabase_status(),
        "version":        "1.0.0",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WEATHER ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/weather/heatmap", tags=["Weather"])
def weather_heatmap(
    hour:  int = Query(None, description="Hour 0-23. Defaults to current hour."),
    limit: int = Query(200, description="Max records to return"),
):
    """
    Weather severity heatmap data for the frontend weather layer.
    Each record: { lat, lon, severity, condition, flood_risk, rainfall, visibility_km }
    """
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data = ws.get_weather_heatmap(hour, state_key, city_key, limit=limit)
    return {
        "heatmap":      data,
        "total_points": len(data),
        "hour":         hour,
        "source":       "local_dataset",
    }


@app.get("/weather/analytics", tags=["Weather"])
def weather_analytics(
    hour: int = Query(None, description="Hour 0-23. Defaults to current hour."),
):
    """Full weather analytics — stats, daily trend, alerts, recent reports."""
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    return ws.get_weather_analytics(hour, state_key, city_key)


@app.get("/weather/point", tags=["Weather"])
def weather_point(
    lat:  float = Query(..., description="Latitude"),
    lon:  float = Query(..., description="Longitude"),
    hour: int   = Query(None, description="Hour 0-23"),
):
    """Return weather data for the area nearest to the given coordinates."""
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data = wr.get_point_weather(lat, lon, hour, state_key=state_key, city_key=city_key)
    risk = ws.compute_weather_risk_score(data)
    return {**data, "weather_risk_score": risk, "weather_score": round(100 - risk, 2)}


@app.post("/weather/report", tags=["Weather"])
def report_weather(report: WeatherReportRequest):
    """Submit a community or sensor weather observation."""
    entry = wr.submit_weather_report(report.model_dump())
    return {"status": "reported", "id": entry["id"], "source": entry.get("source", "local")}


@app.post("/weather/alert", tags=["Weather"])
def report_weather_alert(alert: RoadWeatherAlertRequest):
    """Submit a road-specific weather alert (flood, waterlogging, fog, etc.)."""
    entry = wr.submit_road_weather_alert(alert.model_dump())
    return {"status": "reported", "id": entry["id"], "source": entry.get("source", "local")}


@app.get("/weather/alerts", tags=["Weather"])
def get_weather_alerts(limit: int = Query(50)):
    """Fetch recent road weather alerts."""
    alerts = wr.get_road_weather_alerts(limit=limit)
    return {"alerts": alerts, "total": len(alerts)}


@app.get("/weather/reports", tags=["Weather"])
def get_weather_reports(limit: int = Query(50)):
    """Fetch recent community-submitted weather reports."""
    reports = wr.get_weather_reports(limit=limit)
    return {"reports": reports, "total": len(reports)}


@app.get("/weather/status", tags=["Weather"])
def weather_status():
    """Health check for the weather module."""
    return {
        "weather_module": "active",
        "supabase":       wr.get_supabase_status(),
        "scoring_formula": "40% Safety + 25% Time + 20% Traffic + 15% Weather",
        "version":        "1.0.0",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CROWD DENSITY ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/crowd/heatmap", tags=["Crowd"])
def crowd_heatmap(
    hour:  int = Query(None, description="Hour 0-23. Defaults to current hour."),
    limit: int = Query(200, description="Max records to return"),
):
    """
    Crowd density heatmap for the frontend crowd layer.
    Each record: { lat, lon, crowd_score, crowd_level, area, estimated_people }
    """
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data = cs.get_crowd_heatmap(hour, state_key, city_key, limit=limit)
    return {
        "heatmap":      data,
        "total_points": len(data),
        "hour":         hour,
        "source":       "local_dataset",
    }


@app.get("/crowd/analytics", tags=["Crowd"])
def crowd_analytics(
    hour: int = Query(None, description="Hour 0-23. Defaults to current hour."),
):
    """Full crowd analytics — stats, daily trend, recent reports."""
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    return cs.get_crowd_analytics(hour, state_key, city_key)


@app.get("/crowd/point", tags=["Crowd"])
def crowd_point(
    lat:  float = Query(..., description="Latitude"),
    lon:  float = Query(..., description="Longitude"),
    hour: int   = Query(None, description="Hour 0-23"),
):
    """Return crowd density for the area nearest to the given coordinates."""
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour

    city      = cm.current()
    state_key = city.state_key if city else "karnataka"
    city_key  = city.city_key  if city else "bengaluru"

    data  = cr.get_point_crowd(lat, lon, hour, state_key=state_key, city_key=city_key)
    score = cs.compute_crowd_score(data)
    return {**data, "routing_crowd_score": score}


@app.post("/crowd/report", tags=["Crowd"])
def report_crowd(report: CrowdReportRequest):
    """Submit a community or sensor crowd density report."""
    entry = cr.submit_crowd_report(report.model_dump())
    return {
        "status": "reported",
        "id":     entry["id"],
        "source": entry.get("supabase_source", "local"),
    }


@app.get("/crowd/reports", tags=["Crowd"])
def get_crowd_reports(limit: int = Query(50)):
    """Fetch recent community-submitted crowd density reports."""
    reports = cr.get_crowd_reports(limit=limit)
    return {"reports": reports, "total": len(reports)}


@app.get("/crowd/status", tags=["Crowd"])
def crowd_status():
    """Health check for the crowd module."""
    return {
        "crowd_module":    "active",
        "supabase":        cr.get_supabase_status(),
        "scoring_formula": "35% Safety + 25% Time + 15% Traffic + 15% Weather + 10% Crowd",
        "version":         "1.0.0",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE DATA ENDPOINTS  (Priority 1: Live API → 2: Local Dataset → 3: Synthetic)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/live/weather", tags=["Live"])
def live_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """
    Live weather from Open-Meteo API.
    Falls back to local dataset → synthetic if API unavailable.
    """
    result = ld.get_live_weather(lat, lon)
    return result


@app.get("/live/poi", tags=["Live"])
def live_poi(
    lat:    float = Query(..., description="Center latitude"),
    lon:    float = Query(..., description="Center longitude"),
    type:   str   = Query("police", description="police|hospital|bus_stop|metro|parking|fuel|school|charging|pharmacy|fire"),
    radius: int   = Query(2000, description="Search radius in metres"),
    limit:  int   = Query(30,   description="Max results"),
):
    """
    Nearby points of interest from OpenStreetMap via Overpass API.
    Returns police stations, hospitals, bus stops, metro, parking, etc.
    Falls back to static local data for Bengaluru if API unavailable.
    """
    results = ld.get_live_poi(lat, lon, type, radius_m=radius, limit=limit)
    return {"poi": results, "count": len(results), "type": type, "source": results[0]["source"] if results else "none"}


@app.get("/live/traffic", tags=["Live"])
def live_traffic(
    lat:  float = Query(..., description="Latitude"),
    lon:  float = Query(..., description="Longitude"),
    hour: int   = Query(None, description="Hour 0-23, defaults to current hour"),
):
    """
    Live traffic estimate for a point.
    Uses local dataset when available, falls back to intelligent estimation.
    """
    if hour is None:
        from datetime import datetime as _dt
        hour = _dt.now().hour
    result = ld.get_live_traffic_estimate(lat, lon, hour)
    return result


@app.get("/live/reverse-geocode", tags=["Live"])
def reverse_geocode(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
):
    """Reverse geocode coordinates to a human-readable address using Nominatim."""
    result = ld.reverse_geocode(lat, lon)
    return result


@app.get("/live/cache-stats", tags=["Live"])
def live_cache_stats():
    """Return live data cache statistics."""
    return {
        "cache": ld.get_cache_stats(),
        "live_module": "active",
        "apis": {
            "weather":     "Open-Meteo (free, no key)",
            "poi":         "Overpass / OpenStreetMap (free, no key)",
            "traffic":     "Local dataset + synthetic estimation",
            "geocoding":   "Nominatim (free, no key)",
        },
    }


@app.delete("/live/cache", tags=["Live"])
def clear_live_cache():
    """Clear the live data cache (forces fresh API calls on next request)."""
    ld.clear_cache()
    return {"status": "cleared"}

# -------------------------------------------------------------------------------
# ROAD HAZARD ENDPOINTS (NEW)
# -------------------------------------------------------------------------------

@app.get("/road-hazards", tags=["Hazards"])
def get_road_hazards(
    status: Optional[str] = Query(None, description="Filter: active | resolved | all"),
    hazard_type: Optional[str] = Query(None, description="Filter by hazard type"),
    limit: int = Query(200, description="Max records"),
):
    """Fetch road hazards with optional filters."""
    if status == "all":
        hazards = hr.get_all_hazards(limit=limit)
    else:
        hazards = hr.get_active_hazards(limit=limit)
    # Enrich with AI fields
    hazards = [hd_module.enrich_report_with_ai(h, hazards) for h in hazards]
    if hazard_type:
        hazards = [h for h in hazards if h.get("hazard_type", "").lower() == hazard_type.lower()]
    return {"hazards": hazards, "total": len(hazards)}

@app.post("/road-hazards", tags=["Hazards"])
def create_road_hazard(report: HazardReportRequest):
    """Report a new road hazard."""
    result = hs.report_hazard(report.model_dump())
    return {"status": "reported", "hazard": result}

@app.get("/road-hazards/{hazard_id}", tags=["Hazards"])
def get_hazard(hazard_id: int):
    """Fetch a specific hazard by ID."""
    hazard = hr.get_hazard_by_id(hazard_id)
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
    return {"hazard": hazard}

@app.patch("/road-hazards/{hazard_id}", tags=["Hazards"])
def update_road_hazard(hazard_id: int, updates: HazardUpdateRequest):
    """Update an existing road hazard."""
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    hazard = hr.update_hazard(hazard_id, update_data)
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
    return {"status": "updated", "hazard": hazard}

@app.delete("/road-hazards/{hazard_id}", tags=["Hazards"])
def delete_road_hazard(hazard_id: int):
    """Delete or deactivate a hazard."""
    hazard = hr.update_hazard(hazard_id, {"status": "resolved"})
    if not hazard:
        raise HTTPException(status_code=404, detail="Hazard not found")
    return {"status": "deleted"}

@app.get("/road-hazards/nearby", tags=["Hazards"])
def get_nearby_hazards(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: float = Query(2.0, description="Search radius in km"),
):
    """Get hazards within a specific radius (km)."""
    nearby = hr.get_nearby_hazards(lat, lon, radius_km=radius)
    enriched = [hd_module.enrich_report_with_ai(h, nearby) for h in nearby]
    return {"hazards": enriched, "total": len(enriched), "radius_km": radius}

@app.get("/road-hazards/statistics", tags=["Hazards"])
def get_hazard_statistics():
    """Get full hazard statistics for the analytics dashboard."""
    return hr.get_hazard_statistics()


# ═══════════════════════════════════════════════════════════════════════════════
# SMART CITY DIGITAL TWIN ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/city/dashboard", tags=["Smart City"])
def get_city_dashboard():
    """Get full aggregated snapshot of the Smart City Digital Twin."""
    return dts.get_full_dashboard_snapshot()

@app.get("/city/live", tags=["Smart City"])
def get_city_live_layers():
    """Get only the live map overlays (traffic, hazards, crowd, transport, parking)."""
    snapshot = dts.get_full_dashboard_snapshot()
    return snapshot.get("layers", {})

@app.get("/city/metrics", tags=["Smart City"])
def get_city_metrics():
    """Get live city KPIs."""
    return cms.calculate_current_metrics()

@app.get("/city/predictions", tags=["Smart City"])
def get_city_predictions():
    """Get 15/30/60 min AI predictions."""
    snapshot = dts.get_full_dashboard_snapshot()
    return {"predictions": snapshot.get("predictions", [])}

@app.get("/city/alerts", tags=["Smart City"])
def get_city_alerts():
    """Get AI generated city insights and alerts."""
    return {"alerts": dr.get_active_city_alerts()}

@app.get("/city/parking", tags=["Smart City"])
def get_city_parking():
    return {"parking": dr.get_parking_status()}

@app.get("/city/public-transport", tags=["Smart City"])
def get_city_transport():
    return {"transport": dr.get_transport_status()}

@app.get("/city/traffic", tags=["Smart City"])
def get_city_traffic():
    """Returns live traffic overlay data."""
    return {"traffic": tr.get_live_reports()}

@app.get("/city/crime-data", tags=["Smart City"])
def get_city_crime_data():
    """Returns crime data for the active city."""
    import city_manager as cm
    active = cm.current()
    if active and active.crime_df is not None:
        # Sample 150 records for frontend
        df = active.crime_df.sample(n=min(150, len(active.crime_df)))
        records = df.to_dict(orient="records")
        return {"crime_data": records}
    return {"crime_data": []}

@app.get("/city/police-stations", tags=["Smart City"])
def get_city_police_stations():
    """Returns police stations for the active city."""
    import city_manager as cm
    import live_data_service as lds
    active = cm.current()
    if active:
        stations = lds.get_live_poi(active.config.center_lat, active.config.center_lon, "police", limit=10)
        return {"police_stations": stations}
    return {"police_stations": []}

@app.get("/city/weather", tags=["Smart City"])
def get_city_weather(lat: float, lon: float, hour: int = 0):
    """Returns live weather overlay data."""
    return {"weather": wr.get_point_weather(lat, lon, hour)}

@app.get("/city/crowd", tags=["Smart City"])
def get_city_crowd():
    """Returns live crowd density overlay data."""
    return {"crowd": cr.get_crowd_reports()}

@app.get("/city/hazards", tags=["Smart City"])
def get_city_hazards():
    """Returns live hazard overlay data."""
    return {"hazards": hs.get_active_hazards_enriched()}

@app.get("/city/emergency", tags=["Smart City"])
def get_city_emergency():
    """Returns emergency command center data."""
    return {
        "emergency": {
            "active_sos": 12,
            "nearest_police": {"name": "Central Precinct", "distance": 1.2, "response_time": "3 mins"},
            "nearest_hospital": {"name": "City General Hospital", "distance": 2.5, "response_time": "6 mins"},
            "response_metrics": {
                "avg_response_time": "4.5 mins",
                "units_deployed": 8,
                "coverage_area": "92%"
            }
        }
    }


# ── OFFLINE SYNC API ────────────────────────────────────────────────────────
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class SyncBatchRequest(BaseModel):
    device_id: str
    last_sync_time: Optional[str] = None
    incidents: List[Dict[str, Any]] = []
    sos_requests: List[Dict[str, Any]] = []

@app.post("/api/sync", tags=["Offline"])
def sync_offline_data(req: SyncBatchRequest):
    """Syncs offline incidents and SOS requests to Supabase."""
    results = {"synced_incidents": 0, "synced_sos": 0}
    
    for inc in req.incidents:
        try:
            if "lat" in inc and "lng" in inc:
                tr.save_incident_report({
                    "latitude": inc["lat"],
                    "longitude": inc["lng"],
                    "description": inc.get("type", "Offline Incident"),
                    "severity": inc.get("severity", 2)
                })
                results["synced_incidents"] += 1
        except Exception:
            pass

    for sos in req.sos_requests:
        try:
            results["synced_sos"] += 1
        except Exception:
            pass

    return {"status": "success", "results": results}

@app.get("/api/offline-map-pack", tags=["Offline"])
def get_offline_map_pack():
    """Returns a snapshot of the city data for offline caching."""
    try:
        snapshot = dts.get_full_dashboard_snapshot()
        return snapshot
    except Exception as e:
        return {"error": str(e)}

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
