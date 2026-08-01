// Wrapper for IndexedDB using idb
let dbPromise;

if (window.idb) {
    dbPromise = idb.openDB('SafeRouteDB', 1, {
        upgrade(db) {
            if (!db.objectStoreNames.contains('outbox_sos')) {
                db.createObjectStore('outbox_sos', { keyPath: 'id', autoIncrement: true });
            }
            if (!db.objectStoreNames.contains('outbox_incidents')) {
                db.createObjectStore('outbox_incidents', { keyPath: 'id', autoIncrement: true });
            }
            if (!db.objectStoreNames.contains('cached_routes')) {
                db.createObjectStore('cached_routes', { keyPath: 'route_id' });
            }
            if (!db.objectStoreNames.contains('map_pack_snapshot')) {
                db.createObjectStore('map_pack_snapshot', { keyPath: 'timestamp' });
            }
        },
    });
}

window.offlineDB = {
    async saveSOSOffline(data) {
        if (!dbPromise) return;
        const db = await dbPromise;
        const tx = db.transaction('outbox_sos', 'readwrite');
        tx.store.add(data);
        await tx.done;
        console.log("SOS saved offline");
    },
    async saveIncidentOffline(data) {
        if (!dbPromise) return;
        const db = await dbPromise;
        const tx = db.transaction('outbox_incidents', 'readwrite');
        tx.store.add(data);
        await tx.done;
        console.log("Incident saved offline");
    },
    async getPendingIncidents() {
        if (!dbPromise) return [];
        const db = await dbPromise;
        return await db.getAll('outbox_incidents');
    },
    async getPendingSOS() {
        if (!dbPromise) return [];
        const db = await dbPromise;
        return await db.getAll('outbox_sos');
    },
    async clearIncidents() {
        if (!dbPromise) return;
        const db = await dbPromise;
        await db.clear('outbox_incidents');
    },
    async clearSOS() {
        if (!dbPromise) return;
        const db = await dbPromise;
        await db.clear('outbox_sos');
    }
};

window.flushSyncQueue = async function() {
    if (!navigator.onLine) return;
    console.log("Attempting to flush offline queues...");
    try {
        const incidents = await window.offlineDB.getPendingIncidents();
        const sos = await window.offlineDB.getPendingSOS();
        
        if (incidents.length === 0 && sos.length === 0) return;

        const payload = {
            device_id: "browser-" + Math.random().toString(36).substr(2, 9),
            incidents: incidents,
            sos_requests: sos
        };

        const response = await fetch((window.API_BASE || 'http://localhost:8000') + '/api/sync', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            console.log("Successfully synced offline data.");
            await window.offlineDB.clearIncidents();
            await window.offlineDB.clearSOS();
            // Update UI if counter exists
            const counter = document.getElementById('sync-counter');
            if (counter) counter.style.display = 'none';
        }
    } catch (err) {
        console.error("Failed to sync offline data:", err);
    }
};

// Listen for service worker flush command
if (navigator.serviceWorker) {
    navigator.serviceWorker.addEventListener('message', event => {
        if (event.data && event.data.type === 'FLUSH_SYNC') {
            window.flushSyncQueue();
        }
    });
}
