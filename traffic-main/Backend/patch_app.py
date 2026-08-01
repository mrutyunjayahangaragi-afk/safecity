import os

app_path = r'c:\safe\traffic-main\Backend\app.py'

with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
if 'import digital_twin_service' not in content:
    import_statement = """import digital_twin_service as dts
import city_metrics_service as cms
import dashboard_repository as dr
"""
    content = content.replace('import hazard_repository   as hr', 'import hazard_repository   as hr\n' + import_statement)

# 2. Add Endpoints at the end
if '@app.get("/city/dashboard"' not in content:
    endpoints = """
# ═══════════════════════════════════════════════════════════════════════════════
# SMART CITY DIGITAL TWIN ENDPOINTS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/city/dashboard", tags=["Smart City"])
def get_city_dashboard():
    \"\"\"Get full aggregated snapshot of the Smart City Digital Twin.\"\"\"
    return dts.get_full_dashboard_snapshot()

@app.get("/city/live", tags=["Smart City"])
def get_city_live_layers():
    \"\"\"Get only the live map overlays (traffic, hazards, crowd, transport, parking).\"\"\"
    snapshot = dts.get_full_dashboard_snapshot()
    return snapshot.get("layers", {})

@app.get("/city/metrics", tags=["Smart City"])
def get_city_metrics():
    \"\"\"Get live city KPIs.\"\"\"
    return cms.calculate_current_metrics()

@app.get("/city/predictions", tags=["Smart City"])
def get_city_predictions():
    \"\"\"Get 15/30/60 min AI predictions.\"\"\"
    snapshot = dts.get_full_dashboard_snapshot()
    return {"predictions": snapshot.get("predictions", [])}

@app.get("/city/alerts", tags=["Smart City"])
def get_city_alerts():
    \"\"\"Get AI generated city insights and alerts.\"\"\"
    return {"alerts": dr.get_active_city_alerts()}

@app.get("/city/parking", tags=["Smart City"])
def get_city_parking():
    return {"parking": dr.get_parking_status()}

@app.get("/city/public-transport", tags=["Smart City"])
def get_city_transport():
    return {"transport": dr.get_transport_status()}
"""
    content += "\n" + endpoints

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Appended /city endpoints to app.py")
