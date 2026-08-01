import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import route_engine as re


def test_route_comparison_returns_distinct_candidates():
    result = re.find_route_comparison(12.9716, 77.5946, 12.9352, 77.6245, hour=22)
    assert 'routes' in result
    routes = result['routes']
    assert len(routes) >= 3

    def signature(route):
        return (
            round(route['distance_km'], 2),
            int(route['duration_min']),
            int(route['safety_score']),
            route['risk_level'],
        )

    sigs = [signature(route) for route in routes]
    assert len(set(sigs)) >= 3


def test_emergency_mode_returns_priority_route():
    result = re.find_route_comparison(
        12.9716,
        77.5946,
        12.9352,
        77.6245,
        hour=22,
        emergency_mode=True,
        vehicle_type="Ambulance",
    )
    assert result.get('emergency_mode') is True
    routes = result['routes']
    assert len(routes) == 1
    route = routes[0]
    assert route['type'] == 'Emergency Priority'
    assert route['emergency_priority_score'] > 0
    assert route['road_availability'] >= 0
    assert route['eta'] >= route['duration_min']
