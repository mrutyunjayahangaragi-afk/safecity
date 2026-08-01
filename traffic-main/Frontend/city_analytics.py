import os
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

# Adjust sys path so we can import backend services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../Backend"))
import digital_twin_service as dts

OUT_DIR = os.path.join(os.path.dirname(__file__), "../analytics")

DARK_BG = "#030712"
PANEL_BG = "#111827"
ACCENT = "#06B6D4"
PRIMARY = "#4F46E5"
WARNING = "#F59E0B"
DANGER = "#EF4444"
TEXT = "#F9FAFB"

plt.rcParams.update({
    "figure.facecolor": DARK_BG,
    "axes.facecolor": PANEL_BG,
    "axes.edgecolor": "#1f2937",
    "axes.labelcolor": TEXT,
    "axes.titlecolor": TEXT,
    "xtick.color": "#9CA3AF",
    "ytick.color": "#9CA3AF",
    "text.color": TEXT,
    "grid.color": "#1f2937",
    "grid.linestyle": "--",
})

def generate_city_analytics():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    # Use real data from digital twin service
    snapshot = dts.get_full_dashboard_snapshot()
    
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle("Smart City Digital Twin — Analytics Report", fontsize=22, fontweight="bold", color=TEXT, y=0.96, fontfamily='monospace')
    
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.2, top=0.88, bottom=0.08, left=0.05, right=0.95)
    
    # 1. AI Predictions Line Chart (Top Left)
    ax1 = fig.add_subplot(gs[0, 0])
    horizons = [p["time_horizon"] for p in snapshot.get("predictions", [])]
    traffic = [p["predicted_traffic_index"] for p in snapshot.get("predictions", [])]
    crowd = [p["predicted_crowd_density"] for p in snapshot.get("predictions", [])]
    crime = [p["predicted_crime_risk"] for p in snapshot.get("predictions", [])]
    
    if horizons:
        ax1.plot(horizons, traffic, marker='o', color=PRIMARY, label="Traffic Index", linewidth=2.5)
        ax1.plot(horizons, crowd, marker='s', color=WARNING, label="Crowd Density", linewidth=2.5)
        ax1.plot(horizons, crime, marker='^', color=DANGER, label="Crime Risk", linewidth=2.5)
        ax1.set_xticks([15, 30, 60])
    else:
        ax1.text(0.5, 0.5, 'No Prediction Data', color=TEXT, ha='center', va='center', fontsize=14)

    ax1.set_title("AI Predictive Trends (+60 Mins)", fontweight="bold", fontsize=14)
    ax1.set_xlabel("Minutes from Now")
    ax1.set_ylabel("Risk / Density Index (0-100)")
    ax1.legend(facecolor=PANEL_BG, edgecolor='#1f2937')
    ax1.grid(True)
    
    # 2. Incident & Hazard Distribution Scatter (Top Right)
    ax2 = fig.add_subplot(gs[0, 1])
    hazards = snapshot.get("layers", {}).get("hazards", [])
    traffic_reports = snapshot.get("layers", {}).get("traffic", [])
    
    hx = [h.get("longitude", h.get("lng", 0)) for h in hazards if h.get("longitude", h.get("lng"))]
    hy = [h.get("latitude", h.get("lat", 0)) for h in hazards if h.get("latitude", h.get("lat"))]
    
    tx = [t.get("longitude", t.get("lng", 0)) for t in traffic_reports if t.get("longitude", t.get("lng"))]
    ty = [t.get("latitude", t.get("lat", 0)) for t in traffic_reports if t.get("latitude", t.get("lat"))]
    
    if hx and hy:
        ax2.scatter(hx, hy, c=WARNING, s=100, alpha=0.7, edgecolors='none', label='Hazards', marker='^')
    if tx and ty:
        ax2.scatter(tx, ty, c=PRIMARY, s=60, alpha=0.5, edgecolors='none', label='Traffic Issues')
        
    ax2.set_title("Live Geospatial Incident Distribution", fontweight="bold", fontsize=14)
    ax2.set_xlabel("Longitude")
    ax2.set_ylabel("Latitude")
    ax2.legend(facecolor=PANEL_BG, edgecolor='#1f2937')
    ax2.grid(True)

    # 3. Parking Occupancy Horizontal Bar (Bottom Left)
    ax3 = fig.add_subplot(gs[1, 0])
    parking = snapshot.get("layers", {}).get("parking", [])
    if parking:
        names = [p["name"] for p in parking]
        occ = [p["occupancy_percent"] for p in parking]
        
        # Color coding: >90% Red, >70% Orange, else Cyan
        colors = [DANGER if o > 90 else WARNING if o > 70 else ACCENT for o in occ]
        ax3.barh(names, occ, color=colors, alpha=0.85)
        ax3.set_xlim(0, 100)
    else:
        ax3.text(0.5, 0.5, 'No Parking Data', color=TEXT, ha='center', va='center', fontsize=14)
        
    ax3.set_title("Live Parking Occupancy", fontweight="bold", fontsize=14)
    ax3.set_xlabel("Occupancy (%)")
    ax3.grid(axis='x')
    
    # 4. Public Transport Status Donut (Bottom Right)
    ax4 = fig.add_subplot(gs[1, 1])
    transport = snapshot.get("layers", {}).get("transport", [])
    if transport:
        on_time = len([t for t in transport if t.get("status") == "ON_TIME"])
        delayed = len(transport) - on_time
        
        wedges, texts, autotexts = ax4.pie(
            [on_time, delayed], 
            labels=[f"On Time ({on_time})", f"Delayed ({delayed})"], 
            colors=[ACCENT, DANGER], 
            autopct="%1.1f%%", 
            startangle=90, 
            wedgeprops={"edgecolor": DARK_BG, "linewidth": 2, "width": 0.4}, 
            textprops={"color": TEXT, "fontsize": 12, "fontweight": "bold"}
        )
    else:
        ax4.text(0.5, 0.5, 'No Transport Data', color=TEXT, ha='center', va='center', fontsize=14)

    ax4.set_title("Public Transport Reliability", fontweight="bold", fontsize=14)
    
    out_path = os.path.join(OUT_DIR, "city_analytics.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    print(f"[OK] Enhanced City Analytics Dashboard saved -> {out_path}")

if __name__ == "__main__":
    generate_city_analytics()
