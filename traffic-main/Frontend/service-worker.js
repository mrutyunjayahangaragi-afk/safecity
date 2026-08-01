const CACHE_NAME = 'saferoute-v3';
const ASSETS = [
    '/',
    '/index.html',
    '/dashboard.html',
    '/manifest.json',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdn.jsdelivr.net/npm/idb@7/build/umd.js'
];

// Install Event
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => {
            console.log('Caching App Shell');
            return cache.addAll(ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate Event
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys
                .filter(key => key !== CACHE_NAME)
                .map(key => caches.delete(key))
            );
        })
    );
    return self.clients.claim();
});

// Fetch Event
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Dynamic Caching for Map Tiles (Carto/Leaflet)
    if (url.href.includes('basemaps.cartocdn.com') || url.href.includes('tile.openstreetmap.org')) {
        event.respondWith(
            caches.match(event.request).then(cachedResponse => {
                if (cachedResponse) {
                    return cachedResponse;
                }
                return fetch(event.request).then(networkResponse => {
                    return caches.open('saferoute-maps').then(cache => {
                        cache.put(event.request, networkResponse.clone());
                        return networkResponse;
                    });
                }).catch(() => {
                    // Return a generic blank tile if offline and not cached
                    return new Response('', { status: 404, statusText: 'Not Found' });
                });
            })
        );
        return;
    }

    // Network First, fallback to cache for APIs
    if (url.pathname.startsWith('/city/') || url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).then(response => {
                return caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, response.clone());
                    return response;
                });
            }).catch(() => caches.match(event.request))
        );
        return;
    }

    // Cache First for everything else
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request).then(fetchRes => {
                return caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, fetchRes.clone());
                    return fetchRes;
                });
            });
        })
    );
});

// Background Sync
self.addEventListener('sync', event => {
    if (event.tag === 'sync-offline-data') {
        event.waitUntil(flushSyncQueue());
    }
});

async function flushSyncQueue() {
    // This function will be defined or imported via offline_db.js logic
    console.log("Service Worker: Syncing offline data...");
    const clients = await self.clients.matchAll();
    clients.forEach(client => client.postMessage({ type: 'FLUSH_SYNC' }));
}
