import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
keywords = ['landing-page', 'id="hero', 'id="landing', 'id="app"', 'showApp', 'launchApp', 'preview-map', 'launch-btn', 'LANDING PAGE', 'APP SHELL', 'preview-section', 'hero-section', 'feat-section']
seen = set()
for i, l in enumerate(lines, 1):
    for kw in keywords:
        if kw.lower() in l.lower() and i not in seen:
            seen.add(i)
            print(f'{i}: {repr(l.rstrip()[:140])}')
            break
