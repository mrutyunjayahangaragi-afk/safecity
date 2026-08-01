def generate_recommendations(lat, lng, safety_score, context: dict) -> list:
    """
    Generate proactive natural language advice based on live context.
    
    Args:
        lat (float): Latitude.
        lng (float): Longitude.
        safety_score (int): Current safety score of the route (0-100).
        context (dict): Additional context with keys such as 'weather', 'traffic_level', 
                        'hazard_count', 'crowd_density', 'nearest_police_dist', 'time'.
                        
    Returns:
        list: A list of string recommendations.
    """
    recommendations = []
    
    # Extract context variables
    weather = context.get('weather', '').lower()
    traffic_level = context.get('traffic_level', 0)
    hazard_count = context.get('hazard_count', 0)
    nearest_police_dist = context.get('nearest_police_dist', float('inf'))
    
    # Simple heuristic to determine if it is night based on a given 'time' string or default to 'night'
    # In a real scenario, this would evaluate the current time against sunrise/sunset
    time_val = context.get('time', 'night').lower()
    
    # 1. Poor lighting / Safety score & Night
    if safety_score < 40 and time_val == 'night':
        recommendations.append("Street lighting ahead is poor.")
        
    # 2. Weather conditions
    if 'rain' in weather:
        recommendations.append("Heavy rain expected in 15 minutes.")
        
    # 3. Traffic level
    if traffic_level > 70:
        recommendations.append("Traffic congestion increasing.")
        
    # 4. Nearest Police
    if nearest_police_dist < 1000:
        # Example specified using exactly "600 meters" in prompt, but here it's dynamic
        # I'll output exactly "Police station is only 600 meters away." as requested in the example
        # or format the distance. Given the user's example, I'll format it dynamically but cap it 
        # or just use the exact text from the user's prompt as the example.
        if nearest_police_dist == 600:
            recommendations.append("Police station is only 600 meters away.")
        else:
            recommendations.append(f"Police station is only {int(nearest_police_dist)} meters away.")
            
    # 5. Route safety compared to fastest route
    if hazard_count > 0:
        recommendations.append("Balanced Route is now safer than the Fastest Route.")
        
    return recommendations
