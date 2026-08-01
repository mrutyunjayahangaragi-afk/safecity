import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../Backend")))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

print("=" * 60)
print("SAFEROUTE AI - FULL INTEGRATION TEST")
print("=" * 60)

# 1. Existing Endpoints
print("\n-- Existing Endpoints --")

r = client.get("/")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /               : {r.status_code} [{status}]")

r = client.post("/compare-routes", json={
    "src_lat": 12.9716, "src_lon": 77.5946,
    "dst_lat": 12.9352, "dst_lon": 77.6245,
    "hour": 14, "vehicle_type": "Car"
})
status = "PASS" if r.status_code==200 else "FAIL"
print(f"POST /compare-routes: {r.status_code} [{status}]")
if r.status_code == 200:
    d = r.json()
    print(f"  -> hazard_powered: {d.get('hazard_powered')}")
    print(f"  -> routes: {len(d.get('routes', []))}")

r = client.get("/road-hazards")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /road-hazards   : {r.status_code} [{status}]")

# 2. New Smart City Endpoints
print("\n-- Smart City Digital Twin Endpoints --")

r = client.get("/city/dashboard")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/dashboard : {r.status_code} [{status}]")
if r.status_code == 200:
    d = r.json()
    print(f"  -> status: {d.get('status')}")
    m = d.get('metrics', {})
    print(f"  -> AI Safety Index: {m.get('overall_safety_index')}")
    print(f"  -> Traffic Index:   {m.get('traffic_index')}")
    print(f"  -> Hazard Count:    {m.get('hazard_count')}")
    print(f"  -> Predictions:     {len(d.get('predictions', []))}")
    print(f"  -> Insights:        {len(d.get('insights', []))}")
    layers = d.get('layers', {})
    print(f"  -> Layers: traffic={len(layers.get('traffic',[]))}, transport={len(layers.get('transport',[]))}, parking={len(layers.get('parking',[]))}")

r = client.get("/city/metrics")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/metrics   : {r.status_code} [{status}]")

r = client.get("/city/predictions")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/predictions: {r.status_code} [{status}]")

r = client.get("/city/alerts")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/alerts    : {r.status_code} [{status}]")

r = client.get("/city/parking")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/parking   : {r.status_code} [{status}]")
if r.status_code == 200:
    print(f"  -> parking zones: {len(r.json().get('parking', []))}")

r = client.get("/city/public-transport")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/public-transport: {r.status_code} [{status}]")
if r.status_code == 200:
    print(f"  -> transport units: {len(r.json().get('transport', []))}")

r = client.get("/city/live")
status = "PASS" if r.status_code==200 else "FAIL"
print(f"GET /city/live      : {r.status_code} [{status}]")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
