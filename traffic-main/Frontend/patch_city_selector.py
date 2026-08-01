import re

with open("c:\\safe\\traffic-main\\Frontend\\index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove State Selector and update City Selector
# Let's find the block containing the State and City selectors
ui_block_regex = r'<label class="lbl">State</label>.*?<label class="lbl">City</label>.*?</select>'
new_ui_block = """<label class="lbl">City</label>
        <select class="inp" id="city-sel" onchange="onCityChange()">
          <option value="bengaluru" data-available="true">📍 Bengaluru — Karnataka</option>
          <option value="hyderabad" data-available="true">📍 Hyderabad — Telangana</option>
        </select>"""
content = re.sub(ui_block_regex, new_ui_block, content, flags=re.DOTALL)

# 2. Update onCityChange and onStateChange
# We can remove onStateChange completely.
content = re.sub(r'function onStateChange\(\) \{.*?\}', '', content, flags=re.DOTALL)

# Let's rewrite onCityChange
on_city_change_regex = r'function onCityChange\(\) \{.*?\}'
new_on_city_change = """function onCityChange() {
  var cityKey  = document.getElementById('city-sel').value;
  var stateKey = cityKey === 'hyderabad' ? 'telangana' : 'karnataka';
  var msg = document.getElementById('city-unavail-msg');
  msg.style.display = 'none'; 
  switchCity(stateKey, cityKey);
}"""
content = re.sub(on_city_change_regex, new_on_city_change, content, flags=re.DOTALL)

# 3. Update detectCityFromGPS
detect_gps_regex = r'function detectCityFromGPS\(\) \{.*?(?=\nfunction |\n/\*|</script>)'
new_detect_gps = """function detectCityFromGPS() {
  if (!navigator.geolocation) { notify('Geolocation not supported', 'danger'); return; }
  notify('Detecting your location...', 'info');
  navigator.geolocation.getCurrentPosition(pos => {
    var lat = pos.coords.latitude, lon = pos.coords.longitude;
    fetch('http://localhost:8000/resolve-city?lat=' + lat + '&lon=' + lon, { signal: AbortSignal.timeout(8000) })
    .then(r => r.json())
    .then(data => {
      if (data.found && (data.city_key === 'bengaluru' || data.city_key === 'hyderabad')) {
        notify('📍 Detected: ' + data.city_label, 'success');
        var cs = document.getElementById('city-sel');
        for (var j = 0; j < cs.options.length; j++) if (cs.options[j].value === data.city_key)  { cs.selectedIndex = j; break; }
        onCityChange();
      } else {
        notify('Currently SafeRoute AI supports Bengaluru and Hyderabad.', 'info');
      }
    })
    .catch(() => notify('GPS resolve failed - backend may be offline.', 'info'));
  }, () => notify('Location access denied. Select city manually.', 'info'));
}
"""
content = re.sub(detect_gps_regex, new_detect_gps, content, flags=re.DOTALL)

# Write back
with open("c:\\safe\\traffic-main\\Frontend\\index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("UI Simplification patch applied successfully")
