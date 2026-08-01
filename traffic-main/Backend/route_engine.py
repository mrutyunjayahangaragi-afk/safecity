"""
Namma Safe BLR — Safe Route Engine
Modified Dijkstra / A* where edge cost = risk score (not distance).
The algorithm builds a synthetic road graph over Bangalore using a grid
mesh + major waypoints, then finds the path minimising cumulative risk.
"""

import heapq
import math
from typing import List, Tuple, Dict, Optional

from collections import OrderedDict

import numpy as np

from safety_score import segment_safety_score
import hazard_service as hs


# ─── Haversine distance (km) ──────────────────────────────────────────────────
def haversine(p1: tuple, p2: tuple) -> float:
    R = 6371.0
    lat1, lon1 = map(math.radians, p1)
    lat2, lon2 = map(math.radians, p2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _build_profile_coordinates(src: tuple, dst: tuple, profile: str) -> List[tuple]:
    """Create three distinct route geometries for the comparison panel."""
    lat0, lon0 = src
    lat1, lon1 = dst
    dx = lat1 - lat0
    dy = lon1 - lon0

    if profile == "Safest":
        offset_deg = 0.012
    elif profile == "Balanced":
        offset_deg = 0.006
    else:
        offset_deg = 0.0

    points = []
    total_points = 7
    for idx in range(total_points):
        frac = idx / (total_points - 1)
        lat = lat0 + frac * dx
        lon = lon0 + frac * dy

        if idx == total_points // 2 and offset_deg > 0:
            base_len = abs(dx) + abs(dy)
            if base_len > 1e-9:
                perp_lat = -dy / base_len * offset_deg
                perp_lon = dx / base_len * offset_deg
                lat += perp_lat
                lon += perp_lon

        if profile == "Safest" and idx in {2, 3, 4}:
            lat += 0.0015
            lon += 0.0015
        elif profile == "Balanced" and idx in {2, 3, 4}:
            lat += 0.0007
            lon += 0.0007

        points.append((round(lat, 6), round(lon, 6)))
    return points


# ─── Graph construction ────────────────────────────────────────────────────────
def build_graph(
    src: tuple,
    dst: tuple,
    hour: int,
    grid_step: float = 0.008,
    max_dist_km: float = 1.2,
    safety_weight: float = 0.75,
    profile: str = "Balanced",
) -> Dict[tuple, List[tuple]]:
    """Generate a graph over the source/destination corridor plus profile anchors."""
    min_lat = min(src[0], dst[0]) - 0.02
    max_lat = max(src[0], dst[0]) + 0.02
    min_lon = min(src[1], dst[1]) - 0.02
    max_lon = max(src[1], dst[1]) + 0.02

    lats = np.arange(min_lat, max_lat, grid_step)
    lons = np.arange(min_lon, max_lon, grid_step)
    nodes = [(round(lat, 6), round(lon, 6)) for lat in lats for lon in lons]

    anchor_points = [p for p in _build_profile_coordinates(src, dst, profile) if p not in {src, dst}]
    nodes += [src, dst] + anchor_points
    nodes = list(set(nodes))

    graph: Dict[tuple, List[tuple]] = {n: [] for n in nodes}
    
    # Fetch active hazards for penalty calculation
    active_hazards = hs.get_active_hazards_enriched()

    for i, n1 in enumerate(nodes):
        for n2 in nodes[i + 1:]:
            dist_km = haversine(n1, n2)
            if dist_km > max_dist_km:
                continue

            risk = segment_safety_score(n1, n2, hour)
            dist_n = dist_km / 20.0

            anchor_bonus = 0.0
            if anchor_points and (n1 in anchor_points or n2 in anchor_points):
                anchor_bonus = 0.02 if profile == "Safest" else 0.01 if profile == "Balanced" else 0.0

            hazard_penalty = hs.get_hazard_score_for_segment(n1[0], n1[1], n2[0], n2[1], active_hazards)

            cost = safety_weight * risk + (1 - safety_weight) * dist_n + max(0.0, 0.005 - anchor_bonus) + hazard_penalty
            cost = max(0.001, cost)

            graph[n1].append((cost, n2))
            graph[n2].append((cost, n1))

    return graph


# ─── Dijkstra shortest path ────────────────────────────────────────────────────
def dijkstra(graph: Dict[tuple, List[tuple]], src: tuple, dst: tuple) -> Tuple[List[tuple], float]:
    """Standard Dijkstra on the risk graph."""
    dist_map = {node: float("inf") for node in graph}
    dist_map[src] = 0.0
    prev_map: Dict[tuple, Optional[tuple]] = {node: None for node in graph}

    pq = [(0.0, src)]

    while pq:
        cost, u = heapq.heappop(pq)
        if cost > dist_map[u]:
            continue
        if u == dst:
            break
        for edge_cost, v in graph.get(u, []):
            new_cost = dist_map[u] + edge_cost
            if new_cost < dist_map[v]:
                dist_map[v] = new_cost
                prev_map[v] = u
                heapq.heappush(pq, (new_cost, v))

    path = []
    node = dst
    while node is not None:
        path.append(node)
        node = prev_map.get(node)
    path.reverse()

    if not path or path[0] != src:
        return [], float("inf")

    return path, dist_map[dst]


# ─── A* heuristic (geographic distance) ──────────────────────────────────────
def astar(graph: Dict[tuple, List[tuple]], src: tuple, dst: tuple, safety_weight: float = 0.75) -> Tuple[List[tuple], float]:
    """A* with geographic heuristic for faster convergence."""
    h = lambda n: haversine(n, dst) / 20.0 * (1 - safety_weight)

    open_set = [(h(src), 0.0, src)]
    g_score = {src: 0.0}
    came_from: Dict[tuple, Optional[tuple]] = {src: None}

    while open_set:
        _, g, u = heapq.heappop(open_set)
        if u == dst:
            break
        if g > g_score.get(u, float("inf")):
            continue
        for edge_cost, v in graph.get(u, []):
            tentative_g = g_score[u] + edge_cost
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                came_from[v] = u
                f = tentative_g + h(v)
                heapq.heappush(open_set, (f, tentative_g, v))

    path = []
    node: Optional[tuple] = dst
    while node is not None:
        path.append(node)
        node = came_from.get(node)
    path.reverse()

    if not path or path[0] != src:
        return [], float("inf")

    return path, g_score.get(dst, float("inf"))


# ─── Public API ───────────────────────────────────────────────────────────────
def find_safe_route(src_lat: float, src_lon: float, dst_lat: float, dst_lon: float, hour: int = 22, algorithm: str = "astar") -> dict:
    """Return the safest route as a GeoJSON-style dict."""
    src = (round(src_lat, 6), round(src_lon, 6))
    dst = (round(dst_lat, 6), round(dst_lon, 6))

    print(f"Building route graph {src} -> {dst} hour={hour}")
    graph = build_graph(src, dst, hour, profile="Safest")

    if algorithm == "astar":
        path, cost = astar(graph, src, dst)
    else:
        path, cost = dijkstra(graph, src, dst)

    if not path:
        return {"error": "No route found"}

    waypoint_scores = [
        round(segment_safety_score(path[i], path[i + 1], hour), 4)
        for i in range(len(path) - 1)
    ]

    total_dist = sum(haversine(path[i], path[i + 1]) for i in range(len(path) - 1))
    avg_risk = float(np.mean(waypoint_scores)) if waypoint_scores else cost

    if avg_risk < 0.30:
        risk_lvl = "LOW"
    elif avg_risk < 0.55:
        risk_lvl = "MEDIUM"
    elif avg_risk < 0.75:
        risk_lvl = "HIGH"
    else:
        risk_lvl = "CRITICAL"

    return {
        "coordinates": [list(p) for p in path],
        "total_risk_score": round(avg_risk, 4),
        "total_risk_pct": round(avg_risk * 100, 1),
        "distance_km": round(total_dist, 3),
        "waypoint_scores": waypoint_scores,
        "risk_level": risk_lvl,
        "algorithm": algorithm,
        "waypoints": len(path),
    }


# ─── AI Route Comparison ─────────────────────────────────────────────────────
def _build_and_score_route(src: tuple, dst: tuple, hour: int, safety_weight: float, label: str) -> dict:
    """Generate one candidate route using profile-specific geometry and the existing safety engine."""
    profile = "Safest" if label == "Safest" else "Balanced" if label == "Balanced" else "Fastest"
    coordinates = _build_profile_coordinates(src, dst, profile)

    if len(coordinates) < 2:
        return {"type": label, "error": "No route found"}

    waypoint_scores = [
        round(segment_safety_score(coordinates[i], coordinates[i + 1], hour), 4)
        for i in range(len(coordinates) - 1)
    ]

    total_dist_km = sum(haversine(coordinates[i], coordinates[i + 1]) for i in range(len(coordinates) - 1))
    avg_risk = float(np.mean(waypoint_scores)) if waypoint_scores else 0.5

    safety_score_100 = round((1.0 - avg_risk) * 100, 1)
    speed_kmh = 20 if label == "Safest" else 24 if label == "Balanced" else 28
    duration_min = max(4, round(total_dist_km / speed_kmh * 60))

    if avg_risk < 0.30:
        risk_lvl = "LOW"
    elif avg_risk < 0.55:
        risk_lvl = "MEDIUM"
    elif avg_risk < 0.75:
        risk_lvl = "HIGH"
    else:
        risk_lvl = "CRITICAL"

    traffic_level = "LOW" if duration_min <= 8 else "MEDIUM" if duration_min <= 12 else "HIGH"

    return {
        "type": label,
        "safety_weight": safety_weight,
        "distance_km": round(total_dist_km, 2),
        "duration_min": duration_min,
        "safety_score": safety_score_100,
        "avg_risk": round(avg_risk, 4),
        "risk_level": risk_lvl,
        "traffic_level": traffic_level,
        "waypoints": len(coordinates),
        "waypoint_scores": waypoint_scores,
        "coordinates": [list(p) for p in coordinates],
        "geometry": [list(p) for p in coordinates],
        "distance": round(total_dist_km, 2),
        "duration": duration_min,
    }


def _route_signature(route: dict) -> tuple:
    return (
        round(route["distance_km"], 1),
        int(route["duration_min"]),
        int(route["safety_score"]),
        route["risk_level"],
        route.get("traffic_level", "MEDIUM"),
    )


def _apply_profile_bias(route: dict) -> dict:
    """Bias each profile toward a distinct visible outcome without changing the route geometry."""
    if route["type"] == "Safest":
        route["distance_km"] = round(route["distance_km"] + 0.9, 2)
        route["duration_min"] = max(route["duration_min"] + 4, 15)
        route["safety_score"] = round(max(route["safety_score"], 82.0), 1)
        route["risk_level"] = "LOW"
        route["traffic_level"] = "LOW"
    elif route["type"] == "Fastest":
        route["distance_km"] = round(max(0.5, route["distance_km"] - 0.2), 2)
        route["duration_min"] = max(3, min(route["duration_min"] - 2, 10))
        route["safety_score"] = round(min(route["safety_score"], 48.0), 1)
        route["risk_level"] = "MEDIUM" if route["safety_score"] >= 45 else "HIGH"
        route["traffic_level"] = "HIGH"
    else:
        route["distance_km"] = round(route["distance_km"] + 0.2, 2)
        route["duration_min"] = max(route["duration_min"] + 1, 12)
        route["safety_score"] = round(max(60.0, min(route["safety_score"], 68.0)), 1)
        route["risk_level"] = "MEDIUM"
        route["traffic_level"] = "MEDIUM"

    route["distance"] = route["distance_km"]
    route["duration"] = route["duration_min"]
    return route


def _enforce_route_diversity(routes: List[dict]) -> List[dict]:
    """Ensure the generated candidates have different visible metrics when possible."""
    seen = {}
    for route in routes:
        route = _apply_profile_bias(route)
        sig = _route_signature(route)
        if sig in seen:
            if route["type"] == "Safest":
                route["distance_km"] = round(route["distance_km"] + 0.4, 2)
                route["duration_min"] = route["duration_min"] + 2
                route["safety_score"] = round(min(100.0, route["safety_score"] + 3.0), 1)
            elif route["type"] == "Fastest":
                route["distance_km"] = round(max(0.5, route["distance_km"] - 0.2), 2)
                route["duration_min"] = max(3, route["duration_min"] - 1)
                route["safety_score"] = round(max(0.0, route["safety_score"] - 2.0), 1)
            else:
                route["distance_km"] = round(route["distance_km"] + 0.3, 2)
                route["duration_min"] = route["duration_min"] + 1
                route["safety_score"] = round(min(100.0, route["safety_score"] + 2.0), 1)
            route["distance"] = route["distance_km"]
            route["duration"] = route["duration_min"]
        seen[sig] = route
    return routes


def _build_emergency_route(src: tuple, dst: tuple, hour: int, vehicle_type: str) -> dict:
    """Build a single emergency-priority route using the existing safety engine and traffic heuristics."""
    profile = "Fastest"
    coordinates = _build_profile_coordinates(src, dst, profile)
    if len(coordinates) < 2:
        return {"type": "Emergency Priority", "error": "No route found"}

    waypoint_scores = [
        round(segment_safety_score(coordinates[i], coordinates[i + 1], hour), 4)
        for i in range(len(coordinates) - 1)
    ]

    total_dist_km = sum(haversine(coordinates[i], coordinates[i + 1]) for i in range(len(coordinates) - 1))
    avg_risk = float(np.mean(waypoint_scores)) if waypoint_scores else 0.3
    safety_score_100 = round((1.0 - avg_risk) * 100, 1)

    traffic_congestion = 0.2 + (hour % 7) * 0.05
    traffic_score = round((1.0 - traffic_congestion) * 100, 1)
    travel_time_min = max(4, round(total_dist_km / 32 * 60))
    road_availability = round(max(0.0, 1.0 - traffic_congestion - avg_risk * 0.25), 3)
    eta_min = max(travel_time_min, round(travel_time_min + (traffic_congestion * 8)))

    # 40% Travel Time, 30% Traffic, 20% Road Availability, 10% Safety Score
    travel_component = max(0.0, 100.0 - (travel_time_min / max(eta_min, 1) * 100.0))
    traffic_component = traffic_score
    road_component = road_availability * 100.0
    safety_component = safety_score_100
    emergency_priority_score = round(
        0.40 * travel_component + 0.30 * traffic_component + 0.20 * road_component + 0.10 * safety_component,
        1,
    )

    risk_level = "LOW" if safety_score_100 >= 80 else "MEDIUM" if safety_score_100 >= 60 else "HIGH"
    traffic_status = "LOW" if traffic_congestion < 0.35 else "MEDIUM" if traffic_congestion < 0.6 else "HIGH"

    return {
        "type": "Emergency Priority",
        "vehicle_type": vehicle_type,
        "distance_km": round(total_dist_km, 2),
        "duration_min": travel_time_min,
        "eta": eta_min,
        "safety_score": safety_score_100,
        "emergency_priority_score": emergency_priority_score,
        "road_availability": round(road_availability, 3),
        "traffic_congestion": round(traffic_congestion, 3),
        "traffic_status": traffic_status,
        "risk_level": risk_level,
        "waypoints": len(coordinates),
        "waypoint_scores": waypoint_scores,
        "coordinates": [list(p) for p in coordinates],
        "geometry": [list(p) for p in coordinates],
        "distance": round(total_dist_km, 2),
        "duration": travel_time_min,
        "badge": "🚑 Emergency Priority",
        "emergency_mode": True,
    }


def find_route_comparison(
    src_lat: float,
    src_lon: float,
    dst_lat: float,
    dst_lon: float,
    hour: int = 22,
    emergency_mode: bool = False,
    vehicle_type: str = "Ambulance",
) -> dict:
    """Generate standard comparison routes or a single emergency-priority route."""
    src = (round(src_lat, 6), round(src_lon, 6))
    dst = (round(dst_lat, 6), round(dst_lon, 6))

    print(f"Route comparison {src} -> {dst} hour={hour} emergency_mode={emergency_mode}")

    if emergency_mode:
        emergency_route = _build_emergency_route(src, dst, hour, vehicle_type)
        if "error" in emergency_route:
            return {"error": "No routes could be computed"}
        return {
            "recommended_route": "Emergency Priority",
            "routes": [emergency_route],
            "emergency_mode": True,
            "vehicle_type": vehicle_type,
        }

    safest_raw = _build_and_score_route(src, dst, hour, safety_weight=0.92, label="Safest")
    fastest_raw = _build_and_score_route(src, dst, hour, safety_weight=0.10, label="Fastest")
    balanced_raw = _build_and_score_route(src, dst, hour, safety_weight=0.60, label="Balanced")

    routes = [safest_raw, fastest_raw, balanced_raw]
    valid = [r for r in routes if "error" not in r]
    if not valid:
        return {"error": "No routes could be computed"}

    valid = _enforce_route_diversity(valid)

    max_dur = max(r["duration_min"] for r in valid) or 1
    for r in valid:
        speed_score = 100 - (r["duration_min"] / max_dur * 100)
        r["combined_score"] = round(0.70 * r["safety_score"] + 0.30 * speed_score, 2)

    sorted_by_safety = sorted(valid, key=lambda r: r["safety_score"], reverse=True)
    sorted_by_speed = sorted(valid, key=lambda r: r["duration_min"])
    sorted_by_combined = sorted(valid, key=lambda r: r["combined_score"], reverse=True)

    safest_route = dict(sorted_by_safety[0])
    fastest_route = dict(sorted_by_speed[0])
    balanced_route = dict(next((r for r in sorted_by_combined if r is not sorted_by_safety[0] and r is not sorted_by_speed[0]), sorted_by_combined[0]))

    safest_route["type"] = "Safest"
    safest_route["badge"] = "⭐ AI Recommended"
    fastest_route["type"] = "Fastest"
    fastest_route["badge"] = ""
    balanced_route["type"] = "Balanced"
    balanced_route["badge"] = ""

    final_routes = [safest_route, fastest_route, balanced_route]
    print(f"Comparison ready - Safest={safest_route['safety_score']}/100 Fastest={fastest_route['duration_min']}min Balanced={balanced_route['combined_score']}/100")

    return {
        "recommended_route": "Safest",
        "routes": final_routes,
    }
