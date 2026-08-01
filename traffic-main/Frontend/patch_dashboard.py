import re

with open("c:\\safe\\traffic-main\\Frontend\\dashboard.html", "r", encoding="utf-8") as f:
    content = f.read()

# Replace hardcoded emergency locations array
content = re.sub(
    r"const mockEmergencyLocations = \[.*?\];",
    """let mockEmergencyLocations = [];

// Fetch live police stations for the active city
fetch('http://127.0.0.1:8000/city/police-stations')
  .then(res => res.json())
  .then(data => {
    if(data.police_stations) {
      mockEmergencyLocations = data.police_stations.map(ps => ({
        lat: ps.lat,
        lng: ps.lon,
        name: ps.name,
        type: '🚓',
        color: '#6366F1'
      }));
      // Redraw map markers
      mockEmergencyLocations.forEach(loc => {
        const markerEl = document.createElement('div');
        markerEl.className = 'pulse-marker';
        markerEl.style.backgroundColor = loc.color;
        markerEl.style.boxShadow = `0 0 15px ${loc.color}`;
        
        L.marker([loc.lat, loc.lng], {
          icon: L.divIcon({ className: '', html: markerEl.outerHTML })
        }).addTo(map).bindPopup(`<div style="color:var(--text1)"><b>${loc.type} ${loc.name}</b></div>`);
      });
      // Center map on the first station if present
      if(mockEmergencyLocations.length > 0) {
          map.setView([mockEmergencyLocations[0].lat, mockEmergencyLocations[0].lng], 12);
      }
    }
  });
""",
    content,
    flags=re.DOTALL
)

# Replace the loop that adds markers (we moved it to the fetch callback)
content = re.sub(
    r"mockEmergencyLocations\.forEach\(loc => \{.*?\}\);",
    "// Markers now added in fetch callback",
    content,
    flags=re.DOTALL
)

with open("c:\\safe\\traffic-main\\Frontend\\dashboard.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Dashboard patch applied")
