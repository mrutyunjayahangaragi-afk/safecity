import re

with open("c:\\safe\\traffic-main\\Frontend\\index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Update _activeCity center logic
content = content.replace(
    "if(cityKey === 'bengaluru') _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru' };",
    "if(cityKey === 'bengaluru') _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru', lat: 12.9716, lon: 77.5946 };"
)
content = content.replace(
    "if(cityKey === 'hyderabad') _activeCity = { state_key: 'telangana', city_key: 'hyderabad', label: 'Hyderabad' };",
    "if(cityKey === 'hyderabad') _activeCity = { state_key: 'telangana', city_key: 'hyderabad', label: 'Hyderabad', lat: 17.3850, lon: 78.4867 };"
)
content = content.replace(
    "var _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru' };",
    "var _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru', lat: 12.9716, lon: 77.5946 };"
)

# Replace pointRisk hardcoding
content = re.sub(
    r"const dc = Math\.sqrt\(\(lat - 12\.9716\) \*\* 2 \+ \(lon - 77\.5946\) \*\* 2\);",
    "const clat = _activeCity.lat || 12.9716; const clon = _activeCity.lon || 77.5946; const dc = Math.sqrt((lat - clat) ** 2 + (lon - clon) ** 2);",
    content
)

with open("c:\\safe\\traffic-main\\Frontend\\index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Frontend patch pointRisk applied")
