import time
from typing import List, Dict, Any

class JourneyMonitor:
    def __init__(self):
        pass

    def analyze_telemetry(self, session_id: str, history: List[Dict[str, Any]], current_telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        events = []
        
        current_time = current_telemetry.get('timestamp', time.time())
        current_speed = current_telemetry.get('speed', 0)
        current_score = current_telemetry.get('safety_score', 100)
        
        # Check high_speed
        if current_speed > 120:
            events.append({
                'type': 'high_speed',
                'description': 'Speed exceeded 120 km/h.',
                'severity': 'high'
            })
            
        # Check user_stopped (speed < 2 km/h for > 3 minutes)
        if current_speed < 2:
            for pt in reversed(history):
                if pt.get('speed', 0) < 2:
                    time_diff = current_time - pt.get('timestamp', current_time)
                    if time_diff > 180:
                        events.append({
                            'type': 'user_stopped',
                            'description': 'User stopped for more than 3 minutes.',
                            'severity': 'medium'
                        })
                        break
                else:
                    break

        # Check rapid_safety_drop (safety_score drops by > 20 points in last 2 mins)
        for pt in reversed(history):
            time_diff = current_time - pt.get('timestamp', current_time)
            if time_diff <= 120:
                past_score = pt.get('safety_score', 100)
                if (past_score - current_score) > 20:
                    events.append({
                        'type': 'rapid_safety_drop',
                        'description': 'Safety score dropped by more than 20 points in 2 minutes.',
                        'severity': 'high'
                    })
                    break
            else:
                break
                
        return events
