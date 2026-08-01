import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../Backend")))

from fastapi.testclient import TestClient
from app import app, hr, hs

# Quick mock for database if Supabase isn't available
def test_app():
    # Insert a dummy hazard
    hs.report_hazard({
        "hazard_type": "pothole",
        "title": "Large pothole on main road",
        "description": "Avoid the left lane",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "severity": 8,
        "user_id": "test_user",
        "source": "community"
    })
    
    # Check hazards endpoint
    client = TestClient(app)
    response = client.get("/road-hazards")
    assert response.status_code == 200
    data = response.json()
    print("Hazards Response:", data)
    
    # Test route comparison
    route_req = {
        "src_lat": 12.9716,
        "src_lon": 77.5946,
        "dst_lat": 12.9352,
        "dst_lon": 77.6245,
        "hour": 22,
        "vehicle_type": "Car"
    }
    route_res = client.post("/compare-routes", json=route_req)
    if route_res.status_code != 200:
        print("Error:", route_res.text)
    else:
        print("Route Comparison Success")
        route_data = route_res.json()
        print("Hazard Powered:", route_data.get("hazard_powered"))
        for r in route_data.get("routes", []):
            print(f"Route: {r['type']}, Combined Score: {r.get('combined_score')}, Hazard Score: {r.get('hazard_score_100')}")

if __name__ == "__main__":
    test_app()
