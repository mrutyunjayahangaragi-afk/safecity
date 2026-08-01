import sys, os
sys.stdout.reconfigure(encoding='utf-8')
size = os.path.getsize('Frontend/index.html')
with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f'index.html: {size:,} bytes ({size//1024} KB), {len(lines)} lines')
print()

checks = [
    ('Leaflet Map', 'leaflet'),
    ('Supabase', 'supabase'),
    ('Google OAuth', 'doGoogleSignIn'),
    ('OTP Auth', 'doVerifyOTP'),
    ('SOS Button', 'triggerSOS'),
    ('Route Comparison', 'runRouteComparison'),
    ('Crime Heatmap', 'heatLayer'),
    ('Preview Map', 'preview-map'),
    ('App Map Init', 'initAppMap'),
    ('Nav bar id', 'id="nav"'),
    ('Auth Modal', 'auth-modal'),
    ('Landing div', 'id="landing"'),
    ('launchApp fn', 'function launchApp'),
    ('PWA SW', 'service-worker'),
    ('Assistant Widget', 'ai-assistant-widget'),
    ('Status Bar', 'status-bar-section'),
    ('Features V2', 'feat-card-v2'),
    ('Tech Stack', 'tech-stack'),
    ('Comparison Table', 'cmp-table'),
    ('FAQ Accordion', 'faq-list'),
    ('Footer', 'site-footer'),
    ('Counter JS', 'animateCounter'),
    ('Typing Effect', 'typeTick'),
    ('Fade Observer', 'IntersectionObserver'),
]

ok = 0
for name, kw in checks:
    found = any(kw in l for l in lines)
    status = 'OK' if found else 'BROKEN'
    if found: ok += 1
    print(f'  [{status}] {name}')

print()
print(f'RESULT: {ok}/{len(checks)} checks passed')
