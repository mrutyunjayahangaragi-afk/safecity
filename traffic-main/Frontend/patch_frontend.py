import re

with open("c:\\safe\\traffic-main\\Frontend\\index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Hyderabad to the dropdown and update city status text
content = re.sub(
    r'<option value="bengaluru" data-available="true">.*? Bengaluru - Pilot City</option>',
    '<option value="bengaluru" data-available="true">📍 Bengaluru - Pilot City</option>\n            <option value="hyderabad" data-available="true">📍 Hyderabad - Active</option>',
    content
)

# 2. Fix _activeCity
content = content.replace(
    "var _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru' };",
    "var _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru' };\nlet crimeDataCache = null;\nlet policeStationsCache = null;"
)

# 3. Replace the CD array with fetch logic.
lines = content.split('\n')
new_lines = []
skip_cd = False
skip_ps = False
for line in lines:
    if line.startswith('const CD = ['):
        skip_cd = True
    if skip_cd:
        if '];' in line and not line.startswith('const PS'):
            skip_cd = False
        continue

    if line.startswith('const PS = ['):
        skip_ps = True
    if skip_ps:
        if '];' in line:
            skip_ps = False
        continue

    new_lines.append(line)

content = '\n'.join(new_lines)

# 4. Inject a new function to fetch dynamic data
fetch_script = """
window.CD = [];
window.PS = [];
async function fetchCityData() {
    try {
        const crimeRes = await fetch('http://127.0.0.1:8000/city/crime-data');
        if (crimeRes.ok) {
            const data = await crimeRes.json();
            window.CD = data.crime_data || [];
        }
        
        const psRes = await fetch('http://127.0.0.1:8000/city/police-stations');
        if (psRes.ok) {
            const data = await psRes.json();
            window.PS = data.police_stations || [];
        }
    } catch(e) {
        console.error('Failed to fetch dynamic data', e);
        window.CD = window.CD || [];
        window.PS = window.PS || [];
    }
}
"""

content = content.replace('// --- MAP & DATA LOGIC ---', '// --- MAP & DATA LOGIC ---\n' + fetch_script)
content = content.replace(
    'buildHeat(); buildCrimes(); buildPolice(); buildSafe(); buildChart();',
    'fetchCityData().then(() => { buildHeat(); buildCrimes(); buildPolice(); buildSafe(); buildChart(); });'
)

# Also update changeCity to update map center and fetch new data
city_switch = """
function changeCity(cityKey) {
  var msg = document.getElementById('city-unavail-msg');
  var sel = document.getElementById('pf-city-select');
  var opt = Array.from(sel.options).find(o => o.value === cityKey);
  var available = opt ? opt.getAttribute('data-available') === 'true' : false;
  
  if (!available) { msg.style.display = 'block'; setCityStatusBar(cityKey, false); notify('Dataset for ' + cityKey + ' not yet available. Bengaluru Pilot is active.', 'info'); return; }
  
  msg.style.display = 'none';
  if(cityKey === 'bengaluru') _activeCity = { state_key: 'karnataka', city_key: 'bengaluru', label: 'Bengaluru' };
  if(cityKey === 'hyderabad') _activeCity = { state_key: 'telangana', city_key: 'hyderabad', label: 'Hyderabad' };
  
  setCityStatusBar(cityKey, true);
  
  // Update Backend
  setSpinner(true);
  fetch('http://127.0.0.1:8000/city/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state_key: _activeCity.state_key, city_key: _activeCity.city_key })
  })
  .then(res => res.json())
  .then(async data => {
    setSpinner(false);
    if(data.status === 'success') {
      notify('Switched to ' + _activeCity.label, 'success');
      // Fetch dynamic POIs
      await fetchCityData();
      
      // Update Map View
      if(map) {
          if(cityKey === 'bengaluru') map.setView([12.9716, 77.5946], 12);
          if(cityKey === 'hyderabad') map.setView([17.3850, 78.4867], 12);
      }
      
      // Refresh Dashboard
      if(typeof refreshDashboard === 'function') refreshDashboard();
      if(typeof loadLayers === 'function') loadLayers();
    } else notify(data.message || 'Location not in supported area. Using Bengaluru.', 'info');
  })
  .catch(e => { setSpinner(false); notify('Backend offline - using Bengaluru Pilot data', 'info'); });
}
"""

# Replace the existing changeCity function with our new one
# We will use regex to replace the old changeCity block
content = re.sub(
    r'function changeCity\(cityKey\) \{.*?(?=\n\n|\nfunction |\n//)',
    city_switch.strip(),
    content,
    flags=re.DOTALL
)

with open("c:\\safe\\traffic-main\\Frontend\\index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("Frontend patch script applied")
