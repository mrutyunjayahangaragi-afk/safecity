# 🛡️ SafeRoute AI
### AI-Powered Safe Navigation for Smart Cities

> **Production-Ready AI SaaS** · Hackathon Grade · Bengaluru Pilot  
> Premium UI · Multi-Provider Auth · Real-Time Data · ML-Powered Routing

---

## 🎯 Overview

SafeRoute AI is a full-stack AI navigation platform that prioritizes **safety over speed** using a multi-factor AI scoring engine.

### Why SafeRoute AI instead of Google Maps?

| Feature | Google Maps | SafeRoute AI |
|---|---|---|
| Route optimization | Distance / Time | **AI Safety Score** |
| Crime awareness | ❌ | ✅ CatBoost ML (96.7% accuracy) |
| Real-time traffic | ✅ | ✅ Live heatmap + alerts |
| Weather routing | ❌ | ✅ Flood risk, visibility, rainfall |
| Crowd density | ❌ | ✅ Zone-level crowd prediction |
| Emergency routing | ❌ | ✅ Ambulance / Police / Fire priority |
| Authentication | — | ✅ Google · Apple · Phone OTP · Email |
| Multi-city support | ✅ | ✅ 7 Karnataka cities (Bengaluru pilot) |
| Offline fallback | ❌ | ✅ Client-side AI when backend offline |

---

## 🏗️ Architecture

```
SafeRoute AI/
├── Frontend/
│   ├── index.html              ← Premium SPA (6900+ lines)
│   │                             Landing page · Auth modal · App view
│   │                             Leaflet map · AI route comparison
│   │                             Real-time layers (traffic/weather/crowd/hazards)
│   └── dashboard.html          ← Smart City Digital Twin Dashboard (1500+ lines)
│                                 Apache ECharts live trends · AI Safety Index KPI
│                                 Live AI Insights feed · Predictive analytics (+15m/+30m/+60m)
│                                 Emergency Command Center · Overlays
│
├── Backend/
│   ├── app.py                  ← FastAPI server (1100+ lines)
│   │                             30+ endpoints · JWT middleware
│   │                             Live URL: https://safecity-n5gl.onrender.com
│   │                             /auth/me · /auth/profile · /compare-routes · /city/dashboard
│   ├── data_processing.py      ← DBSCAN clustering, density grids
│   ├── safety_score.py         ← Composite safety scoring engine
│   ├── risk_model.py           ← CatBoost / LogisticRegression ML inference
│   ├── route_engine.py         ← A* / Dijkstra with safety cost
│   ├── traffic_service.py      ← Traffic enrichment (50/30/20 formula)
│   ├── traffic_repository.py   ← Supabase + local fallback (all persistence)
│   ├── weather_service.py      ← Weather enrichment (40/25/20/15 formula)
│   ├── weather_repository.py   ← Weather data access layer
│   ├── crowd_service.py        ← Crowd enrichment (35/25/15/15/10 formula)
│   ├── crowd_repository.py     ← Crowd data access layer
│   ├── city_manager.py         ← Multi-city state management
│   ├── city_registry.py        ← City configuration registry
│   ├── live_data_service.py    ← Open-Meteo weather + OSM POI integration
│   └── supabase_schema.sql     ← Complete DB schema (12 tables + RLS)
│
├── Data/
│   └── karnataka/
│       ├── bengaluru/          ← Crime · Traffic · Weather · Crowd datasets
│       ├── mysuru/             ← Config (Coming Soon)
│       ├── hubballi/           ← Config (Coming Soon)
│       └── ...5 more cities
│
├── models/
│   └── risk_model.pkl          ← Trained risk model (auto-generated)
│
├── AUTH_SETUP.md               ← Step-by-step auth provider configuration
└── README.md                   ← This file
```

---

## 🔐 Authentication System (v2)

Full multi-provider auth via Supabase. All methods produce a Supabase UUID user, auto-create a profile, and persist all user data with RLS protection.

| Method | Status | Flow |
|---|---|---|
| Email + Password | ✅ | Register → Verify email → Login |
| Google OAuth | ✅ | Click → Google → Redirect → Profile auto-created |
| Apple Sign In | ✅ | Click → Apple → Redirect → Profile auto-created |
| Phone OTP | ✅ | Enter number → SMS OTP → 6-digit verify → Profile created |
| Forgot Password | ✅ | Email → Reset link → New password |

### Profile Fields

```sql
profiles (
  user_id       uuid      -- Supabase auth.users FK
  full_name     text
  email         text
  phone_number  text
  avatar_url    text
  provider      text      -- email | google | apple | phone
  country       text
  city          text
  last_login    timestamptz
  created_at    timestamptz
  updated_at    timestamptz
)
```

### User-Linked Data Tables

Every record references the authenticated `user_id`:

| Table | Purpose |
|---|---|
| `route_history` | Every route the user navigates |
| `saved_routes` | Starred/bookmarked routes |
| `incident_reports` | User-submitted safety reports |
| `traffic_reports` | Community traffic submissions |
| `weather_reports` | Community weather observations |
| `crowd_density_reports` | Community crowd reports |
| `sos_requests` | SOS location broadcasts |
| `emergency_requests` | Emergency vehicle routing |
| `notifications` | In-app alerts and updates |
| `favorite_locations` | Saved pins (home, work, etc.) |
| `recent_searches` | Location search history |

---

## ⚙️ Setup

### 1. Install Python dependencies
```bash
pip install fastapi uvicorn pandas numpy scikit-learn catboost supabase python-dotenv
```

### 2. Configure environment
`Backend/.env` is pre-configured with the Supabase project. Verify:
```
SUPABASE_URL=https://dwrqfzqalxpyqagyfgmr.supabase.co
SUPABASE_KEY=<anon-key>
SUPABASE_SERVICE_KEY=<service-role-key>
```

### 3. Apply SQL schema
Open **Supabase SQL Editor** → paste `Backend/supabase_schema.sql` → Run.

This creates all 12 tables, RLS policies, storage buckets, and auto-create triggers.

### 4. Enable auth providers in Supabase
See **[AUTH_SETUP.md](AUTH_SETUP.md)** for step-by-step instructions for Google, Apple, and Phone (Twilio).

### 5. Start the backend
```bash
cd Backend/
uvicorn app:app --reload --port 8000
```
API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 6. Open the frontend
```
Frontend/index.html  →  open in any modern browser
```
No build step needed. Works offline (client-side AI fallback).

---

## 🌐 API Reference

### Auth Endpoints (JWT Required)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/auth/me` | Returns authenticated user_id from JWT |
| POST | `/auth/profile` | Upsert user profile (requires Bearer token) |
| GET | `/auth/profile` | Fetch own profile (requires Bearer token) |

### Navigation (No Auth Required)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/find-safe-route` | Single safest route (OSRM + AI scoring) |
| POST | `/compare-routes` | AI comparison: Safest / Fastest / Balanced |
| POST | `/emergency/route` | Emergency vehicle priority routing |
| POST | `/predict-risk` | ML risk prediction for a coordinate |

### Data Layers
| Method | Endpoint | Description |
|---|---|---|
| GET | `/get-crime-heatmap` | Crime density grid |
| GET | `/traffic/heatmap` | Real-time congestion heatmap |
| GET | `/weather/heatmap` | Weather severity heatmap |
| GET | `/crowd/heatmap` | Crowd density heatmap |
| GET | `/live/weather` | Live weather (Open-Meteo API) |
| GET | `/live/poi` | OSM points of interest |

### Persistence
| Method | Endpoint | Description |
|---|---|---|
| POST | `/route/history` | Save completed route |
| GET | `/route/history` | Fetch route history |
| POST | `/sos/request` | Submit SOS with location |
| POST | `/incident/report` | Report unsafe area |

### City
| Method | Endpoint | Description |
|---|---|---|
| GET | `/cities` | All cities with availability |
| POST | `/set-city` | Switch active city |
| GET | `/resolve-city` | GPS-based city detection |

### Example: AI Route Comparison
```bash
curl -X POST http://localhost:8000/compare-routes \
  -H "Content-Type: application/json" \
  -d '{
    "src_lat": 12.9716, "src_lon": 77.5946,
    "dst_lat": 12.9352, "dst_lon": 77.6245,
    "hour": 22, "algorithm": "astar"
  }'
```

### Example: Authenticated Profile Upsert
```bash
TOKEN=$(supabase auth token)   # or fetch from frontend
curl -X POST http://localhost:8000/auth/profile \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Arjun", "provider": "google", "city": "Bengaluru"}'
```

---

## 🧠 AI Scoring Formula

### Route Comparison Weights
```
AI Score = 35% Safety
         + 25% Time efficiency
         + 15% Traffic conditions
         + 15% Weather impact
         + 10% Crowd density
```

### Safety Score (per road segment)
```
risk = 0.45 × crime_density
     + 0.20 × (1 − lighting_proximity)
     + 0.20 × time_risk_factor(hour)
     + 0.15 × distance_from_center_penalty
```

### Risk Levels
| Score | Level | Color |
|---|---|---|
| < 0.30 | 🟢 LOW | Green |
| 0.30–0.55 | 🟡 MEDIUM | Amber |
| 0.55–0.75 | 🔴 HIGH | Red |
| > 0.75 | ⛔ CRITICAL | Deep Red |

---

## 🗺️ Map Layers

Toggle any layer independently in the app:

| Layer | Data Source | Update |
|---|---|---|
| Crime Heatmap | CatBoost ML + local dataset | Static per session |
| Crime Incidents | Embedded + Supabase realtime | Live |
| Traffic | `/traffic/heatmap` | Per hour |
| Weather | `/weather/heatmap` | Per hour |
| Crowd Density | `/crowd/heatmap` | Per hour |
| Police Stations | Embedded data | Static |
| Safe Zones | Computed circles | Static |
| Hospitals | OSM Live API | On demand |
| Bus Stops | OSM Live API | On demand |
| Metro Stations | OSM Live API | On demand |
| EV Charging | OSM Live API | On demand |
| Parking | OSM Live API | On demand |

---

## 🔒 Security

| Feature | Implementation |
|---|---|
| Row Level Security | All 12 tables — users only see their own data |
| JWT Verification | Backend decodes Bearer tokens on auth endpoints |
| UUID Foreign Keys | All user_id columns reference `auth.users(id)` |
| Storage RLS | Avatar uploads scoped to user's own folder |
| Input validation | Pydantic models on all POST endpoints |
| OTP rate limiting | 3 retries max, 60-second cooldown |
| Auth state sync | Multi-tab via Supabase `onAuthStateChange` |
| Guest fallback | All navigation features work without login |

---

## 🏙️ Multi-City Support

| City | Status | Dataset |
|---|---|---|
| Bengaluru | ✅ Active (Pilot) | Crime · Traffic · Weather · Crowd |
| Mysuru | 🔜 Coming Soon | Config only |
| Hubballi | 🔜 Coming Soon | Config only |
| Belagavi | 🔜 Coming Soon | Config only |
| Mangaluru | 🔜 Coming Soon | Config only |
| Kalaburagi | 🔜 Coming Soon | Config only |
| Davanagere | 🔜 Coming Soon | Config only |

---

## 📦 Tech Stack

### Frontend
- Vanilla JS (ES6+) — no build step, single HTML file
- Leaflet.js — interactive dark maps
- Leaflet.heat — crime heatmap rendering
- Leaflet.markercluster — crime incident clustering
- Supabase JS SDK v2 — auth, realtime, storage
- Google Fonts (Inter + Space Grotesk) — premium typography
- CSS animations — aurora background, particle system, counters

### Backend
- FastAPI — async REST API
- CatBoost — primary ML model (96.7% accuracy)
- Pandas / NumPy — data processing
- Supabase Python SDK — database + auth
- OSRM — real road routing (public demo server)
- Open-Meteo — live weather API
- OpenStreetMap Nominatim — geocoding
- Overpass API — OSM POI queries

### Database
- Supabase (PostgreSQL) — 12 tables with full RLS
- Supabase Auth — multi-provider authentication
- Supabase Storage — avatar + incident image buckets
- Supabase Realtime — live incident/traffic/SOS channels

---

## 🏆 Hackathon Demo Script

**1. Landing Page (10 seconds)**
- Animated aurora background, live stat counters (250K+ routes, 98% accuracy)
- Click "Find Safe Route" → enters the app

**2. Authentication (30 seconds)**
- Click "Get Started" on nav → auth modal opens
- Show social buttons: Google, Apple, Phone
- Demo Phone OTP: enter number → receive SMS → enter 6-digit code
- Profile auto-created, user data linked

**3. Route Finding (60 seconds)**
- Search "MG Road" → "Koramangala"
- Set hour to 22:00 (night)
- Click "Find Safest Route"
- Watch 4-step AI process: OSRM → Safety Scoring → Traffic → Comparison
- AI route cards appear: Safest (green glow) / Fastest / Balanced
- Each card shows: Score, Distance, ETA, Traffic, Weather, Crowd, AI bar
- Click "Choose Route" → color-coded route on map

**4. Live Layers (30 seconds)**
- Toggle Traffic Layer → congestion heatmap
- Toggle Weather Layer → flood risk overlay
- Toggle Crowd Layer → density circles
- Toggle Hospitals → OSM live data loads

**5. Emergency Mode (20 seconds)**
- Enable "Emergency Priority" toggle
- Select "Ambulance"
- Find route → single emergency priority card

**6. SOS + Incident (20 seconds)**
- Click SOS → location broadcast saved to Supabase
- Click "Report Unsafe Area" → click on map → submit

**7. Profile & Data (10 seconds)**
- Click user badge → profile panel
- Shows name, email, provider badge, joined date, routes this session
- Edit name, upload avatar

**Judges' attention points:**
- Everything works offline (client-side AI fallback)
- Real road geometry from OSRM, not straight lines
- 5-factor AI scoring (crime + traffic + weather + crowd + time)
- Production-ready auth: Google OAuth, Apple, Phone OTP all live
- RLS means zero data leakage between users

---

## 📄 Files Modified in v2

| File | Change |
|---|---|
| `Frontend/index.html` | Complete premium redesign + full auth system |
| `Backend/app.py` | JWT middleware + `/auth/*` endpoints |
| `Backend/supabase_schema.sql` | Full rewrite — 12 tables, triggers, RLS, storage |
| `AUTH_SETUP.md` | New — step-by-step provider config guide |
| `README.md` | This file — complete update |
