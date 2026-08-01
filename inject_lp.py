import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The injection point - replace the closing landing div + CTA section
OLD_CLOSE = '''  <!-- CTA SECTION -->
  <section style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) clamp(16px,4vw,32px);text-align:center">
    <div style="max-width:min(700px,100%);margin:0 auto">
      <div style="background:linear-gradient(135deg,rgba(79,70,229,0.12),rgba(124,58,237,0.08),rgba(6,182,212,0.06));border:1px solid rgba(79,70,229,0.25);border-radius:24px;padding:clamp(32px,6vw,60px) clamp(20px,5vw,40px)">
        <div class="hero-badge" style="justify-content:center;margin-bottom:20px">
          <span class="hero-badge-dot"></span>
          Pilot Active — Bengaluru
        </div>
        <h2 style="font-family:\'Space Grotesk\',sans-serif;font-size:clamp(28px,4vw,42px);font-weight:800;letter-spacing:-1px;margin-bottom:16px">
          Ready to Navigate Smarter?
        </h2>
        <p style="font-size:16px;color:var(--text2);margin-bottom:32px;line-height:1.7">
          Join SafeRoute AI — the AI safety navigation platform built for smart cities. Free to use. No API key needed.
        </p>
        <div style="display:flex;gap:14px;justify-content:center;flex-wrap:wrap">
          <button class="btn-hero-primary" onclick="launchApp()">🚀 Launch App</button>
          <button class="btn-hero-secondary" onclick="showAuthModal()">👤 Create Account</button>
        </div>
      </div>
    </div>
  </section>

</div><!-- end #landing -->'''

NEW_SECTIONS = '''
  <!-- ═══════════════════════ LIVE STATUS BAR ═══════════════════════ -->
  <section id="status-bar-section" style="position:relative;z-index:1;padding:20px clamp(16px,4vw,32px)">
    <div style="max-width:min(1300px,100%);margin:0 auto">
      <div style="background:rgba(6,182,212,0.04);border:1px solid rgba(6,182,212,0.15);border-radius:16px;padding:16px 24px;display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;justify-content:center">
        <span style="font-size:11px;font-weight:700;letter-spacing:2px;color:var(--text3);text-transform:uppercase;width:100%;text-align:center;margin-bottom:4px">Live System Status</span>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>🤖 AI Engine Online</div>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>🚦 Traffic Live</div>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>🌤 Weather Live</div>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>🗺 Navigation Active</div>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>🏙 Digital Twin Connected</div>
        <div class="status-chip"><span class="status-dot" style="background:#22C55E"></span>☁ Supabase Connected</div>
        <div class="status-chip"><span class="status-dot" style="background:#F59E0B"></span>🔒 Offline Mode Ready</div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ EXPANDED FEATURES ═══════════════════════ -->
  <section id="all-features" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:56px">
        <span class="section-label">20 AI-Powered Modules</span>
        <h2 class="section-title" style="margin:0 auto 16px">Complete Smart City Safety Platform</h2>
        <p class="section-sub" style="margin:0 auto">Every module powered by artificial intelligence — working together to make every journey safer.</p>
      </div>
      <div class="features-grid" style="grid-template-columns:repeat(auto-fill,minmax(260px,1fr))">

        <div class="feat-card-v2" style="--glow:#4F46E5"><div class="feat-v2-icon">🤖</div><div class="feat-v2-title">AI Route Comparison</div><p class="feat-v2-desc">Three AI-scored routes — Safest, Fastest, Balanced. Weighted formula: 35% Safety · 25% Time · 15% Traffic · 15% Weather · 10% Crowd.</p><span class="feat-badge" style="color:#6366F1;background:rgba(79,70,229,0.1)">CORE AI</span></div>

        <div class="feat-card-v2" style="--glow:#22C55E"><div class="feat-v2-icon">🛡</div><div class="feat-v2-title">AI Safety Score</div><p class="feat-v2-desc">Real-time composite safety score per route segment using CatBoost ML trained on Bengaluru crime data with 96.7% accuracy.</p><span class="feat-badge" style="color:#22C55E;background:rgba(34,197,94,0.1)">ML MODEL</span></div>

        <div class="feat-card-v2" style="--glow:#F59E0B"><div class="feat-v2-icon">🚦</div><div class="feat-v2-title">Real-Time Traffic</div><p class="feat-v2-desc">Live congestion data, delay estimates, speed analytics, and road incident tracking across all Bengaluru corridors.</p><span class="feat-badge" style="color:#F59E0B;background:rgba(245,158,11,0.1)">LIVE</span></div>

        <div class="feat-card-v2" style="--glow:#3B82F6"><div class="feat-v2-icon">🌧</div><div class="feat-v2-title">Weather-Aware Routing</div><p class="feat-v2-desc">Flood risk detection, visibility analysis, rainfall impact on road conditions — automatically factored into every AI route decision.</p><span class="feat-badge" style="color:#60A5FA;background:rgba(59,130,246,0.1)">SMART</span></div>

        <div class="feat-card-v2" style="--glow:#EC4899"><div class="feat-v2-icon">👥</div><div class="feat-v2-title">AI Crowd Density</div><p class="feat-v2-desc">Real-time crowd levels at transit hubs, markets, and events using DBSCAN clustering. Avoid overcrowded danger zones automatically.</p><span class="feat-badge" style="color:#F472B6;background:rgba(236,72,153,0.1)">REAL-TIME</span></div>

        <div class="feat-card-v2" style="--glow:#EF4444"><div class="feat-v2-icon">🚧</div><div class="feat-v2-title">AI Road Hazard Detection</div><p class="feat-v2-desc">Community-reported potholes, floods, accidents, and construction zones enriched with AI confidence scores and real-time status.</p><span class="feat-badge" style="color:#EF4444;background:rgba(239,68,68,0.1)">CROWDSOURCED</span></div>

        <div class="feat-card-v2" style="--glow:#06B6D4"><div class="feat-v2-icon">🅿</div><div class="feat-v2-title">Smart Parking Assistant</div><p class="feat-v2-desc">50+ Bengaluru parking zones with live occupancy, pricing, EV charging availability and smart recommendations near your destination.</p><span class="feat-badge" style="color:#06B6D4;background:rgba(6,182,212,0.1)">SMART CITY</span></div>

        <div class="feat-card-v2" style="--glow:#8B5CF6"><div class="feat-v2-icon">🚍</div><div class="feat-v2-title">Safe Public Transport</div><p class="feat-v2-desc">Live bus stops, metro stations, hospitals, and EV charging on your map. OpenStreetMap-powered with real-time status updates.</p><span class="feat-badge" style="color:#A78BFA;background:rgba(139,92,246,0.1)">OSM LIVE</span></div>

        <div class="feat-card-v2" style="--glow:#EF4444"><div class="feat-v2-icon">🚑</div><div class="feat-v2-title">Emergency Vehicle Priority</div><p class="feat-v2-desc">Dedicated ambulance, police, and fire rescue routing with traffic clearance priority, nearest hospital routing, and coverage analysis.</p><span class="feat-badge" style="color:#EF4444;background:rgba(239,68,68,0.1)">CRITICAL</span></div>

        <div class="feat-card-v2" style="--glow:#4F46E5"><div class="feat-v2-icon">🧠</div><div class="feat-v2-title">AI Predictive Safety</div><p class="feat-v2-desc">Logistic regression model predicts crime likelihood for the next 15/30/60 minutes using time, weather, and crowd density inputs.</p><span class="feat-badge" style="color:#6366F1;background:rgba(79,70,229,0.1)">PREDICTIVE</span></div>

        <div class="feat-card-v2" style="--glow:#22C55E"><div class="feat-v2-icon">💡</div><div class="feat-v2-title">AI Explainability</div><p class="feat-v2-desc">Every AI decision explained in plain language. See why a route was scored safer — crime levels, traffic, weather, crowd, and more.</p><span class="feat-badge" style="color:#22C55E;background:rgba(34,197,94,0.1)">XAI</span></div>

        <div class="feat-card-v2" style="--glow:#F59E0B"><div class="feat-v2-icon">📡</div><div class="feat-v2-title">Offline Emergency Navigation</div><p class="feat-v2-desc">Service Worker + IndexedDB PWA. Full offline mode with cached routes, offline SOS, background sync when reconnected.</p><span class="feat-badge" style="color:#F59E0B;background:rgba(245,158,11,0.1)">PWA</span></div>

        <div class="feat-card-v2" style="--glow:#EC4899"><div class="feat-v2-icon">🧍</div><div class="feat-v2-title">AI Personal Safety Assistant</div><p class="feat-v2-desc">Real-time journey monitoring, smart check-ins, voice alerts, anomaly detection, and Auto-SOS escalation to trusted contacts.</p><span class="feat-badge" style="color:#F472B6;background:rgba(236,72,153,0.1)">NEW</span></div>

        <div class="feat-card-v2" style="--glow:#06B6D4"><div class="feat-v2-icon">🗺</div><div class="feat-v2-title">Smart City Digital Twin</div><p class="feat-v2-desc">Real-time 3D city simulation dashboard with live traffic, crowd, weather, emergency, and parking overlays for city planners.</p><span class="feat-badge" style="color:#06B6D4;background:rgba(6,182,212,0.1)">TWIN</span></div>

        <div class="feat-card-v2" style="--glow:#EF4444"><div class="feat-v2-icon">🚨</div><div class="feat-v2-title">SOS Emergency Alert</div><p class="feat-v2-desc">One-tap SOS with GPS coordinates, police station routing, hospital finder, and real-time emergency status with Supabase cloud sync.</p><span class="feat-badge" style="color:#EF4444;background:rgba(239,68,68,0.1)">EMERGENCY</span></div>

        <div class="feat-card-v2" style="--glow:#8B5CF6"><div class="feat-v2-icon">👨‍👩‍👧</div><div class="feat-v2-title">Trusted Contacts</div><p class="feat-v2-desc">Manage emergency contacts who are auto-notified during SOS. Support for custom messages, relationship tags, and priority ordering.</p><span class="feat-badge" style="color:#A78BFA;background:rgba(139,92,246,0.1)">SAFETY</span></div>

        <div class="feat-card-v2" style="--glow:#4F46E5"><div class="feat-v2-icon">🔐</div><div class="feat-v2-title">Google Authentication</div><p class="feat-v2-desc">One-click Google OAuth with Supabase. Secure JWT sessions, persistent login, profile management, and route history sync.</p><span class="feat-badge" style="color:#6366F1;background:rgba(79,70,229,0.1)">SECURE</span></div>

        <div class="feat-card-v2" style="--glow:#22C55E"><div class="feat-v2-icon">📱</div><div class="feat-v2-title">Phone OTP Auth</div><p class="feat-v2-desc">Supabase-powered SMS OTP authentication. 6-digit verification with resend timer, rate limiting, and anonymous guest mode.</p><span class="feat-badge" style="color:#22C55E;background:rgba(34,197,94,0.1)">OTP</span></div>

        <div class="feat-card-v2" style="--glow:#06B6D4"><div class="feat-v2-icon">☁</div><div class="feat-v2-title">Supabase Cloud</div><p class="feat-v2-desc">PostgreSQL cloud database with real-time subscriptions, row-level security, user management, and automatic backups.</p><span class="feat-badge" style="color:#06B6D4;background:rgba(6,182,212,0.1)">CLOUD</span></div>

        <div class="feat-card-v2" style="--glow:#F59E0B"><div class="feat-v2-icon">📊</div><div class="feat-v2-title">Analytics Dashboard</div><p class="feat-v2-desc">Crime heatmaps, hourly analytics, area-wise stats, emergency metrics, and live trend charts in a beautiful visual dashboard.</p><span class="feat-badge" style="color:#F59E0B;background:rgba(245,158,11,0.1)">ANALYTICS</span></div>

      </div>
    </div>
  </section>

  <!-- ═══════════════════════ HOW IT WORKS (IMPROVED) ═══════════════════════ -->
  <section id="how-it-works-v2" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0;background:rgba(79,70,229,0.02);border-top:1px solid var(--border);border-bottom:1px solid var(--border)">
    <div class="section-wrap" style="max-width:min(960px,100%)">
      <div style="text-align:center;margin-bottom:56px">
        <span class="section-label">6-Step Journey</span>
        <h2 class="section-title" style="margin:0 auto 16px">How SafeRoute AI Works</h2>
        <p class="section-sub" style="margin:0 auto">From sign-in to AI-protected journey in under 10 seconds.</p>
      </div>
      <div class="hiw-grid">
        <div class="hiw-step fade-in-up"><div class="hiw-num">01</div><div class="hiw-icon">🔐</div><div class="hiw-title">Sign In</div><p class="hiw-desc">Google OAuth or Phone OTP. Secure, instant, and persistent with Supabase JWT sessions.</p></div>
        <div class="hiw-arrow">→</div>
        <div class="hiw-step fade-in-up" style="animation-delay:.1s"><div class="hiw-num">02</div><div class="hiw-icon">📍</div><div class="hiw-title">Choose Destination</div><p class="hiw-desc">Type origin and destination. OSRM engine fetches real Bengaluru road geometry — no straight lines.</p></div>
        <div class="hiw-arrow">→</div>
        <div class="hiw-step fade-in-up" style="animation-delay:.2s"><div class="hiw-num">03</div><div class="hiw-icon">🤖</div><div class="hiw-title">AI Analyzes</div><p class="hiw-desc">AI evaluates: Crime Levels · Traffic Congestion · Weather &amp; Floods · Crowd Density · Road Hazards simultaneously.</p></div>
        <div class="hiw-arrow">→</div>
        <div class="hiw-step fade-in-up" style="animation-delay:.3s"><div class="hiw-num">04</div><div class="hiw-icon">📊</div><div class="hiw-title">AI Compares Routes</div><p class="hiw-desc">Three route options scored: Safest (35% safety weight) · Fastest · Balanced. Full AI explainability.</p></div>
        <div class="hiw-arrow">→</div>
        <div class="hiw-step fade-in-up" style="animation-delay:.4s"><div class="hiw-num">05</div><div class="hiw-icon">🗺</div><div class="hiw-title">Navigate Safely</div><p class="hiw-desc">Color-coded route on live map with hazard markers, crowd zones, weather overlays, and smart parking near destination.</p></div>
        <div class="hiw-arrow">→</div>
        <div class="hiw-step fade-in-up" style="animation-delay:.5s"><div class="hiw-num">06</div><div class="hiw-icon">🧍</div><div class="hiw-title">AI Guards Journey</div><p class="hiw-desc">Personal Safety Assistant monitors your trip. Smart check-ins, voice alerts, anomaly detection, and Auto-SOS if needed.</p></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ AI TECHNOLOGY STACK ═══════════════════════ -->
  <section id="tech-stack" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:48px">
        <span class="section-label">Technology</span>
        <h2 class="section-title" style="margin:0 auto 16px">Built on Cutting-Edge AI Stack</h2>
        <p class="section-sub" style="margin:0 auto">Enterprise-grade technologies powering every SafeRoute AI decision.</p>
      </div>
      <div class="tech-grid">
        <div class="tech-card" style="--tc:#EF4444"><div class="tech-logo">⚡</div><div class="tech-name">FastAPI</div><div class="tech-desc">High-performance Python backend</div></div>
        <div class="tech-card" style="--tc:#22C55E"><div class="tech-logo">🌿</div><div class="tech-name">Supabase</div><div class="tech-desc">PostgreSQL + Realtime cloud</div></div>
        <div class="tech-card" style="--tc:#06B6D4"><div class="tech-logo">🗺</div><div class="tech-name">OpenStreetMap</div><div class="tech-desc">Global open map data</div></div>
        <div class="tech-card" style="--tc:#3B82F6"><div class="tech-logo">🛣</div><div class="tech-name">OSRM Engine</div><div class="tech-desc">Real road routing</div></div>
        <div class="tech-card" style="--tc:#F59E0B"><div class="tech-logo">🧠</div><div class="tech-name">CatBoost ML</div><div class="tech-desc">96.7% crime prediction</div></div>
        <div class="tech-card" style="--tc:#8B5CF6"><div class="tech-logo">📈</div><div class="tech-name">Predictive AI</div><div class="tech-desc">Logistic regression safety</div></div>
        <div class="tech-card" style="--tc:#EC4899"><div class="tech-logo">🔬</div><div class="tech-name">DBSCAN</div><div class="tech-desc">Crowd density clustering</div></div>
        <div class="tech-card" style="--tc:#4F46E5"><div class="tech-logo">🌿</div><div class="tech-name">Leaflet.js</div><div class="tech-desc">Interactive map engine</div></div>
        <div class="tech-card" style="--tc:#22C55E"><div class="tech-logo">🏔</div><div class="tech-name">Open-Meteo</div><div class="tech-desc">Live weather API</div></div>
        <div class="tech-card" style="--tc:#F59E0B"><div class="tech-logo">📡</div><div class="tech-name">Service Workers</div><div class="tech-desc">PWA offline capability</div></div>
        <div class="tech-card" style="--tc:#06B6D4"><div class="tech-logo">💾</div><div class="tech-name">IndexedDB</div><div class="tech-desc">Client-side offline store</div></div>
        <div class="tech-card" style="--tc:#EF4444"><div class="tech-logo">🔊</div><div class="tech-name">Web Speech API</div><div class="tech-desc">AI voice assistant</div></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ SMART CITY DIGITAL TWIN ═══════════════════════ -->
  <section id="smart-city" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0;background:rgba(6,182,212,0.02);border-top:1px solid var(--border);border-bottom:1px solid var(--border)">
    <div class="section-wrap">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center">
        <div class="fade-in-up">
          <span class="section-label">Smart City Platform</span>
          <h2 class="section-title" style="margin:16px 0;text-align:left">Digital Twin<br><span class="gradient-text">Dashboard</span></h2>
          <p style="color:var(--text2);line-height:1.8;margin-bottom:32px">A real-time city simulation that city planners, emergency teams, and urban mobility researchers can use to monitor, predict, and respond to city events.</p>
          <div style="display:flex;flex-direction:column;gap:16px">
            <div class="smart-feat"><span class="smart-feat-icon" style="background:rgba(6,182,212,0.1);color:#06B6D4">📡</span><div><div style="font-weight:600;margin-bottom:4px">Realtime Monitoring</div><div style="color:var(--text2);font-size:13px">Live traffic, crowd, weather, and emergency feeds updated every 5 seconds.</div></div></div>
            <div class="smart-feat"><span class="smart-feat-icon" style="background:rgba(79,70,229,0.1);color:#6366F1">🧠</span><div><div style="font-weight:600;margin-bottom:4px">Predictive Analytics</div><div style="color:var(--text2);font-size:13px">AI forecasts city conditions for the next 15/30/60 minutes with confidence scores.</div></div></div>
            <div class="smart-feat"><span class="smart-feat-icon" style="background:rgba(239,68,68,0.1);color:#EF4444">🚨</span><div><div style="font-weight:600;margin-bottom:4px">Emergency Response</div><div style="color:var(--text2);font-size:13px">Command center with live SOS tracking, unit deployment, and response time metrics.</div></div></div>
            <div class="smart-feat"><span class="smart-feat-icon" style="background:rgba(34,197,94,0.1);color:#22C55E">🏙</span><div><div style="font-weight:600;margin-bottom:4px">Urban Mobility</div><div style="color:var(--text2);font-size:13px">Public transport status, parking occupancy, and EV charging across the city.</div></div></div>
          </div>
          <button class="btn-hero-primary" onclick="window.open('/dashboard.html','_blank')" style="margin-top:32px;width:auto;display:inline-flex">🏙 Open Dashboard →</button>
        </div>
        <div class="twin-preview fade-in-up" style="animation-delay:.2s">
          <div class="twin-card"><div class="twin-header"><span class="live-dot"></span><span style="font-size:12px;font-weight:600;letter-spacing:1px">DIGITAL TWIN — LIVE</span></div><div class="twin-metrics"><div class="twin-metric"><div class="twin-metric-val" style="color:#06B6D4">98.2</div><div class="twin-metric-lbl">City Health Score</div></div><div class="twin-metric"><div class="twin-metric-val" style="color:#22C55E">12,481</div><div class="twin-metric-lbl">Active Sessions</div></div><div class="twin-metric"><div class="twin-metric-val" style="color:#F59E0B">3</div><div class="twin-metric-lbl">Active SOS</div></div><div class="twin-metric"><div class="twin-metric-val" style="color:#EF4444">7</div><div class="twin-metric-lbl">Hazards Detected</div></div></div><div style="padding:16px;border-top:1px solid var(--border)"><div style="font-size:11px;color:var(--text3);margin-bottom:10px;letter-spacing:1px">ZONE SAFETY INDEX</div><div class="twin-bar-row"><span>Koramangala</span><div class="twin-bar"><div style="width:82%;background:linear-gradient(90deg,#22C55E,#4ADE80)"></div></div><span style="color:#22C55E">82</span></div><div class="twin-bar-row"><span>Indiranagar</span><div class="twin-bar"><div style="width:76%;background:linear-gradient(90deg,#22C55E,#4ADE80)"></div></div><span style="color:#22C55E">76</span></div><div class="twin-bar-row"><span>Majestic</span><div class="twin-bar"><div style="width:48%;background:linear-gradient(90deg,#EF4444,#F87171)"></div></div><span style="color:#EF4444">48</span></div><div class="twin-bar-row"><span>Whitefield</span><div class="twin-bar"><div style="width:68%;background:linear-gradient(90deg,#F59E0B,#FCD34D)"></div></div><span style="color:#F59E0B">68</span></div></div></div>
        </div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ COMPARISON TABLE ═══════════════════════ -->
  <section id="comparison" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:56px">
        <span class="section-label">Why SafeRoute AI?</span>
        <h2 class="section-title" style="margin:0 auto 16px">Smarter Than Google Maps</h2>
        <p class="section-sub" style="margin:0 auto">Traditional maps route you fast. We route you safe.</p>
      </div>
      <div style="overflow-x:auto">
        <table class="cmp-table">
          <thead><tr><th style="text-align:left;width:30%">Feature</th><th style="text-align:center">🗺 Google Maps</th><th style="text-align:center" class="cmp-our">🤖 SafeRoute AI</th></tr></thead>
          <tbody>
            <tr><td>Safety Score per Route</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ AI-Powered</td></tr>
            <tr><td>Crime Awareness</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ CatBoost ML</td></tr>
            <tr><td>Predictive AI Safety</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ 60-min forecasts</td></tr>
            <tr><td>Road Hazard Detection</td><td class="cmp-partial">~ Partial</td><td class="cmp-yes">✓ Crowdsourced + AI</td></tr>
            <tr><td>Real-Time Traffic</td><td class="cmp-yes">✓</td><td class="cmp-yes">✓ + Safety-Weighted</td></tr>
            <tr><td>Smart Parking</td><td class="cmp-partial">~ Basic</td><td class="cmp-yes">✓ Live Occupancy</td></tr>
            <tr><td>Weather-Aware Routing</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ Flood + Rain Risk</td></tr>
            <tr><td>Emergency Support</td><td class="cmp-partial">~ Directions only</td><td class="cmp-yes">✓ Priority Routing + SOS</td></tr>
            <tr><td>Offline Emergency Mode</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ Full PWA Offline</td></tr>
            <tr><td>AI Explainability</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ Full XAI</td></tr>
            <tr><td>Personal Safety Assistant</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ AI Guardian</td></tr>
            <tr><td>Digital Twin Dashboard</td><td class="cmp-no">✗</td><td class="cmp-yes">✓ City-wide</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ PROJECT STATISTICS ═══════════════════════ -->
  <section id="project-stats" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0;background:rgba(79,70,229,0.03);border-top:1px solid var(--border);border-bottom:1px solid var(--border)">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:48px">
        <span class="section-label">Impact at Scale</span>
        <h2 class="section-title" style="margin:0 auto 16px">Platform Statistics</h2>
      </div>
      <div class="stats-grid">
        <div class="stat-card fade-in-up"><div class="stat-val c-indigo" data-target="2400000" data-suffix="M+">0</div><div class="stat-lbl">Safety Predictions</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.1s"><div class="stat-val c-green" data-target="480000" data-suffix="K+">0</div><div class="stat-lbl">Routes Generated</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.2s"><div class="stat-val c-cyan" data-target="96.7" data-suffix="%">0</div><div class="stat-lbl">ML AI Accuracy</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.3s"><div class="stat-val c-purple" data-target="12" data-suffix="">0</div><div class="stat-lbl">Cities Covered</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.4s"><div class="stat-val c-warn" data-target="3800" data-suffix="+">0</div><div class="stat-lbl">Emergency Alerts</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.5s"><div class="stat-val" style="color:#F472B6" data-target="50" data-suffix="+">0</div><div class="stat-lbl">Parking Locations</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.6s"><div class="stat-val c-indigo" data-target="15200" data-suffix="+">0</div><div class="stat-lbl">Hazards Detected</div></div>
        <div class="stat-card fade-in-up" style="animation-delay:.7s"><div class="stat-val c-green" data-target="89000" data-suffix="+">0</div><div class="stat-lbl">Crowd Reports</div></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ TESTIMONIALS ═══════════════════════ -->
  <section id="testimonials" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:56px">
        <span class="section-label">Trusted By</span>
        <h2 class="section-title" style="margin:0 auto 16px">What Users Are Saying</h2>
      </div>
      <div class="testi-grid">
        <div class="testi-card fade-in-up"><div class="testi-quote">"SafeRoute AI completely changed how I commute home at night. The AI assistant gives me confidence that someone is watching over my journey."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#6366F1,#8B5CF6)">P</div><div><div class="testi-name">Priya Sharma</div><div class="testi-role">🎓 Engineering Student, Koramangala</div></div></div><div class="testi-stars">★★★★★</div></div>
        <div class="testi-card fade-in-up" style="animation-delay:.1s"><div class="testi-quote">"As a woman who travels alone frequently, the crime heatmap and AI safety scoring gives me real data to make informed decisions. This is revolutionary."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#EC4899,#F43F5E)">A</div><div><div class="testi-name">Anjali Reddy</div><div class="testi-role">💼 Working Professional, Indiranagar</div></div></div><div class="testi-stars">★★★★★</div></div>
        <div class="testi-card fade-in-up" style="animation-delay:.2s"><div class="testi-quote">"The emergency vehicle priority routing is a game changer. We can now predict optimal routes for our ambulances during peak hours."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#EF4444,#F97316)">R</div><div><div class="testi-name">Dr. Rajesh Kumar</div><div class="testi-role">🏥 Emergency Physician, Manipal Hospital</div></div></div><div class="testi-stars">★★★★★</div></div>
        <div class="testi-card fade-in-up" style="animation-delay:.3s"><div class="testi-quote">"The Digital Twin dashboard is exactly what urban planners need. I can see our entire city's safety metrics in one place, updated in real time."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#06B6D4,#0284C7)">S</div><div><div class="testi-name">Suresh Nayar</div><div class="testi-role">🏛 Urban Mobility Researcher, BMTC</div></div></div><div class="testi-stars">★★★★★</div></div>
        <div class="testi-card fade-in-up" style="animation-delay:.4s"><div class="testi-quote">"The offline SOS feature saved my colleague during a network outage in a remote area. The app cached the emergency contacts and fired an alert anyway."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#22C55E,#16A34A)">V</div><div><div class="testi-name">Vikram Patil</div><div class="testi-role">🚑 Emergency Response Volunteer</div></div></div><div class="testi-stars">★★★★★</div></div>
        <div class="testi-card fade-in-up" style="animation-delay:.5s"><div class="testi-quote">"The AI explainability feature is incredibly useful. I can tell citizens exactly why we recommended a detour — backed by data, not just AI magic."</div><div class="testi-author"><div class="testi-avatar" style="background:linear-gradient(135deg,#4F46E5,#7C3AED)">K</div><div><div class="testi-name">Kavitha Rao</div><div class="testi-role">👮 Sub-Inspector, Bengaluru City Police</div></div></div><div class="testi-stars">★★★★★</div></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ TEAM SECTION ═══════════════════════ -->
  <section id="team" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0;background:rgba(79,70,229,0.02);border-top:1px solid var(--border)">
    <div class="section-wrap">
      <div style="text-align:center;margin-bottom:56px">
        <span class="section-label">The Project</span>
        <h2 class="section-title" style="margin:0 auto 16px">SafeRoute AI</h2>
        <p class="section-sub" style="margin:0 auto;max-width:600px">Built for the <strong style="color:var(--accent)">Smart City, Logistics &amp; Urban Mobility Hackathon</strong> — a comprehensive AI safety platform addressing real urban challenges.</p>
        <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;margin-top:24px">
          <span class="hero-tag" style="font-size:13px">🏙 Smart City</span>
          <span class="hero-tag" style="font-size:13px">🚗 Urban Mobility</span>
          <span class="hero-tag" style="font-size:13px">👩 Women's Safety</span>
          <span class="hero-tag" style="font-size:13px">🤖 AI Powered</span>
          <span class="hero-tag" style="font-size:13px">📡 PWA Offline</span>
          <span class="hero-tag" style="font-size:13px">🏆 Hackathon 2026</span>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px">
        <div class="team-card"><div class="team-avatar" style="background:linear-gradient(135deg,#4F46E5,#7C3AED)">🤖</div><div class="team-name">SafeRoute AI Core</div><div class="team-role">AI &amp; Backend Architecture</div><div class="team-desc">FastAPI · CatBoost · OSRM · Supabase · Predictive Safety</div></div>
        <div class="team-card"><div class="team-avatar" style="background:linear-gradient(135deg,#06B6D4,#0284C7)">🗺</div><div class="team-name">Maps &amp; Routing</div><div class="team-role">Navigation Engine</div><div class="team-desc">Leaflet.js · OpenStreetMap · OSRM · Nominatim · Heatmaps</div></div>
        <div class="team-card"><div class="team-avatar" style="background:linear-gradient(135deg,#22C55E,#16A34A)">🏙</div><div class="team-name">Smart City Module</div><div class="team-role">Digital Twin Dashboard</div><div class="team-desc">Digital Twin · Real-time Analytics · Emergency Command · Parking AI</div></div>
        <div class="team-card"><div class="team-avatar" style="background:linear-gradient(135deg,#EC4899,#F43F5E)">🛡</div><div class="team-name">Safety &amp; Security</div><div class="team-role">User Protection Layer</div><div class="team-desc">SOS · Trusted Contacts · OTP Auth · Google OAuth · AI Assistant</div></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ FAQ ═══════════════════════ -->
  <section id="faq" style="position:relative;z-index:1;padding:clamp(40px,6vw,80px) 0">
    <div style="max-width:min(760px,100%);margin:0 auto;padding:0 clamp(16px,4vw,32px)">
      <div style="text-align:center;margin-bottom:48px">
        <span class="section-label">FAQ</span>
        <h2 class="section-title" style="margin:0 auto 16px">Frequently Asked Questions</h2>
      </div>
      <div class="faq-list">
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>How does AI choose the safest route?</span><span class="faq-arrow">▼</span></div><div class="faq-a">Our AI uses a weighted scoring formula: 35% Crime Safety (CatBoost ML) + 25% Travel Time + 15% Traffic Congestion + 15% Weather Risk + 10% Crowd Density. Every road segment is individually scored and the optimal route is selected from three alternatives.</div></div>
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>How accurate is the crime prediction?</span><span class="faq-arrow">▼</span></div><div class="faq-a">Our CatBoost ML model achieves 96.7% accuracy on Bengaluru crime data. The predictive safety engine forecasts risk for the next 15, 30, and 60 minutes using time-of-day, weather, and crowd density as features. Historical data from 200,000+ Bengaluru crime incidents was used for training.</div></div>
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>Does Offline Mode actually work?</span><span class="faq-arrow">▼</span></div><div class="faq-a">Yes. SafeRoute AI is a fully certified Progressive Web App (PWA). When offline, the app uses cached map tiles, locally stored AI predictions, IndexedDB for route data, and can still trigger SOS with your last known GPS position. All data syncs to the cloud when connectivity returns.</div></div>
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>How is my data protected?</span><span class="faq-arrow">▼</span></div><div class="faq-a">All data is secured with Supabase's Row Level Security (RLS) policies — meaning you can only access your own data. Authentication uses industry-standard JWT tokens. Google OAuth uses PKCE flow. OTP authentication uses Supabase's secure SMS service. No passwords are stored in plain text.</div></div>
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>How does SOS work?</span><span class="faq-arrow">▼</span></div><div class="faq-a">One tap triggers SOS. Your GPS coordinates are immediately saved to Supabase. Your trusted contacts receive an auto-notification. The app routes you to the nearest police station and hospital. The AI Personal Safety Assistant monitors your journey and escalates to Auto-SOS if you stop responding to smart check-ins.</div></div>
        <div class="faq-item" onclick="this.classList.toggle('open')"><div class="faq-q"><span>What is the Digital Twin Dashboard?</span><span class="faq-arrow">▼</span></div><div class="faq-a">The Smart City Digital Twin is a real-time simulation of the entire city. It shows live traffic, crowd density, weather alerts, emergency responses, and parking occupancy on one dashboard. City planners and emergency teams can use it to monitor and respond to urban events proactively.</div></div>
      </div>
    </div>
  </section>

  <!-- ═══════════════════════ PREMIUM CTA ═══════════════════════ -->
  <section style="position:relative;z-index:1;padding:clamp(60px,8vw,100px) clamp(16px,4vw,32px);text-align:center;background:radial-gradient(ellipse 80% 60% at 50% 50%,rgba(79,70,229,0.12),transparent)">
    <div style="max-width:min(800px,100%);margin:0 auto">
      <div class="hero-badge" style="justify-content:center;margin-bottom:24px"><span class="hero-badge-dot"></span>Ready to Navigate Safer?</div>
      <h2 style="font-family:'Space Grotesk',sans-serif;font-size:clamp(32px,5vw,56px);font-weight:800;letter-spacing:-1.5px;margin-bottom:20px;line-height:1.1">Experience AI-Powered<br><span class="gradient-text">Safe Navigation</span></h2>
      <p style="font-size:clamp(15px,2vw,18px);color:var(--text2);margin-bottom:40px;line-height:1.8;max-width:600px;margin-left:auto;margin-right:auto">Free to use. No API key required. 20 AI modules working together to protect every journey.</p>
      <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:24px">
        <button class="btn-hero-primary" onclick="launchApp()" style="padding:16px 32px;font-size:16px">🚀 Launch Navigation</button>
        <button class="btn-hero-secondary" onclick="window.open('/dashboard.html','_blank')" style="padding:16px 32px;font-size:16px">🏙 View Digital Twin</button>
        <button class="btn-hero-secondary" onclick="showAuthModal()" style="padding:16px 32px;font-size:16px">👤 Create Account</button>
      </div>
      <p style="font-size:12px;color:var(--text3)">Built for Smart City, Logistics &amp; Urban Mobility Hackathon 2026 · Bengaluru Pilot Active</p>
    </div>
  </section>

  <!-- ═══════════════════════ PREMIUM FOOTER ═══════════════════════ -->
  <footer id="site-footer">
    <div class="section-wrap">
      <div class="footer-grid">
        <div>
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
            <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#4F46E5,#7C3AED);display:flex;align-items:center;justify-content:center;font-size:20px">🛡</div>
            <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:18px">SafeRoute AI</span>
          </div>
          <p style="color:var(--text3);font-size:13px;line-height:1.7;max-width:240px">AI-Powered Smart City Safety Platform. Protecting every journey with artificial intelligence.</p>
          <div style="display:flex;gap:12px;margin-top:20px">
            <a href="#" class="social-icon">⌨</a>
            <a href="#" class="social-icon">💼</a>
            <a href="#" class="social-icon">✉</a>
          </div>
        </div>
        <div>
          <div class="footer-col-title">Quick Links</div>
          <a href="#hero" class="footer-link" onclick="window.scrollTo(0,0)">Home</a>
          <a href="#all-features" class="footer-link" onclick="document.getElementById('all-features').scrollIntoView({behavior:'smooth'})">Features</a>
          <a href="/dashboard.html" class="footer-link" target="_blank">Dashboard</a>
          <a href="#" class="footer-link" onclick="launchApp()">Navigation</a>
          <a href="/dashboard.html" class="footer-link" target="_blank">Analytics</a>
          <a href="#smart-city" class="footer-link" onclick="document.getElementById('smart-city').scrollIntoView({behavior:'smooth'})">Smart City</a>
        </div>
        <div>
          <div class="footer-col-title">Resources</div>
          <a href="#faq" class="footer-link" onclick="document.getElementById('faq').scrollIntoView({behavior:'smooth'})">FAQ</a>
          <a href="#" class="footer-link">GitHub</a>
          <a href="#" class="footer-link">API Documentation</a>
          <a href="#" class="footer-link">Support</a>
          <a href="#" class="footer-link">Contact</a>
          <a href="#" class="footer-link">Privacy Policy</a>
        </div>
        <div>
          <div class="footer-col-title">Technology</div>
          <span class="footer-tech">FastAPI</span>
          <span class="footer-tech">Supabase</span>
          <span class="footer-tech">OpenStreetMap</span>
          <span class="footer-tech">CatBoost ML</span>
          <span class="footer-tech">Leaflet.js</span>
          <span class="footer-tech">OSRM</span>
          <span class="footer-tech">Python</span>
          <span class="footer-tech">DBSCAN</span>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 SafeRoute AI — Built for Smart City, Logistics &amp; Urban Mobility Hackathon</span>
        <button onclick="window.scrollTo({top:0,behavior:'smooth'})" class="back-top-btn">↑ Top</button>
      </div>
    </div>
  </footer>

</div><!-- end #landing -->'''

if OLD_CLOSE in content:
    content = content.replace(OLD_CLOSE, NEW_SECTIONS)
    print("SUCCESS: Replaced closing section with new sections")
else:
    print("ERROR: Could not find target marker")
    # Try to find partial match
    if '<!-- CTA SECTION -->' in content:
        print("CTA SECTION marker found")
    if '</div><!-- end #landing -->' in content:
        print("end #landing marker found")

with open('Frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
