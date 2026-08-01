import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Bump service worker version to v3
c = c.replace("const CACHE_NAME = 'saferoute-v2';", "const CACHE_NAME = 'saferoute-v3';")

with open('Frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(c)

# Also update service worker file
with open('Frontend/service-worker.js', 'r', encoding='utf-8') as f:
    sw = f.read()
sw = sw.replace("const CACHE_NAME = 'saferoute-v2';", "const CACHE_NAME = 'saferoute-v3';")
with open('Frontend/service-worker.js', 'w', encoding='utf-8') as f:
    f.write(sw)

print('Cache version bumped to v3')
print('Done')
