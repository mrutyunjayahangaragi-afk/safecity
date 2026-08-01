import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as backend

client = TestClient(backend.app)


def test_persistence_endpoints_round_trip():
    profile_resp = client.post(
        "/user/profile",
        json={
            "user_id": "demo-api",
            "display_name": "Demo API",
            "email": "demo-api@example.com",
            "role": "viewer",
        },
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json()["status"] == "saved"

    history_resp = client.post(
        "/route/history",
        json={
            "user_id": "demo-api",
            "route_label": "Safest",
            "source": "A",
            "destination": "B",
            "distance_km": 5.2,
            "duration_min": 14,
        },
    )
    assert history_resp.status_code == 200
    assert history_resp.json()["status"] == "saved"

    sos_resp = client.post(
        "/sos/request",
        json={
            "user_id": "demo-api",
            "latitude": 12.97,
            "longitude": 77.59,
            "message": "Help",
            "status": "active",
        },
    )
    assert sos_resp.status_code == 200
    assert sos_resp.json()["status"] == "created"

    incident_resp = client.post(
        "/incident/report",
        json={
            "user_id": "demo-api",
            "latitude": 12.98,
            "longitude": 77.60,
            "description": "Suspicious",
            "severity": 6,
            "status": "active",
        },
    )
    assert incident_resp.status_code == 200
    assert incident_resp.json()["status"] == "reported"
