import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import route_engine as re

res = re.find_route_comparison(12.9716, 77.5946, 12.9352, 77.6245, hour=22)
routes = res['routes']
print('route_count', len(routes))
for route in routes:
    print(route['type'], route['distance_km'], route['duration_min'], route['safety_score'], route['risk_level'], route['traffic_level'])
