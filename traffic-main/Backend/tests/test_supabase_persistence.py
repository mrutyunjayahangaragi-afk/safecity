import traffic_repository as tr


def test_persistence_crud_round_trip():
    tr.reset_persistence_state()

    profile = tr.save_user_profile({
        "user_id": "user-1",
        "display_name": "Alex",
        "email": "alex@example.com",
        "phone": "9999999999",
        "role": "viewer",
    })
    assert profile["user_id"] == "user-1"
    assert tr.get_user_profiles("user-1")[0]["display_name"] == "Alex"

    route = tr.save_route_history({
        "user_id": "user-1",
        "route_label": "Safest",
        "source": "MG Road",
        "destination": "Koramangala",
        "distance_km": 6.2,
        "duration_min": 18,
    })
    assert route["route_label"] == "Safest"
    assert tr.get_route_history("user-1")[0]["destination"] == "Koramangala"

    sos = tr.save_sos_request({
        "user_id": "user-1",
        "latitude": 12.97,
        "longitude": 77.59,
        "message": "Need help",
    })
    assert sos["status"] == "active"
    assert tr.get_sos_requests("user-1")[0]["message"] == "Need help"

    incident = tr.save_incident_report({
        "user_id": "user-1",
        "latitude": 12.98,
        "longitude": 77.60,
        "description": "Suspicious area",
        "severity": 7,
    })
    assert incident["description"] == "Suspicious area"
    assert tr.get_incident_reports("user-1")[0]["severity"] == 7
