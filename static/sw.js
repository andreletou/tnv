// Service Worker for Marketplace PWA

const CACHE_NAME = 'marketplace-v1';
const STATIC_CACHE = 'marketplace-static-v1';
const DYNAMIC_CACHE = 'marketplace-dynamic-v1';

const STATIC_ASSETS = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/js/api.js',
    '/static/manifest.json',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => self.clients.claim())
    );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip external API calls
    if (url.origin !== location.origin && !url.pathname.startsWith('/api/')) {
        return;
    }
    
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {
                // Return cached version if available
                if (cachedResponse) {
                    // For API calls, try network first but serve cache if offline
                    if (url.pathname.startsWith('/api/')) {
                        return fetch(request)
                            .then(networkResponse => {
                                // Cache successful network responses
                                if (networkResponse.ok) {
                                    return caches.open(DYNAMIC_CACHE)
                                        .then(cache => {
                                            cache.put(request, networkResponse.clone());
                                            return networkResponse;
                                        });
                                }
                                return cachedResponse;
                            })
                            .catch(() => cachedResponse);
                    }
                    
                    // For static assets, serve from cache
                    return cachedResponse;
                }
                
                // For static assets, try network then cache
                if (STATIC_ASSETS.includes(url.pathname) || 
                    url.pathname.startsWith('/static/') ||
                    url.pathname === '/') {
                    return fetch(request)
                        .then(networkResponse => {
                            if (networkResponse.ok) {
                                return caches.open(DYNAMIC_CACHE)
                                    .then(cache => {
                                        cache.put(request, networkResponse.clone());
                                        return networkResponse;
                                    });
                            }
                            throw new Error('Network response was not ok');
                        })
                        .catch(() => {
                            // Return offline page for navigation requests
                            if (request.mode === 'navigate') {
                                return caches.match('/offline.html');
                            }
                        });
                }
                
                // For all other requests, try network
                return fetch(request);
            })
            .catch(error => {
                console.log('Service Worker: Fetch failed:', error);
                
                // Return offline page for navigation requests
                if (request.mode === 'navigate') {
                    return caches.match('/offline.html');
                }
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync-cart') {
        event.waitUntil(syncCart());
    }
    if (event.tag === 'background-sync-orders') {
        event.waitUntil(syncOrders());
    }
});

// Push notifications
self.addEventListener('push', event => {
    const options = {
        body: event.data ? event.data.text() : 'Nouvelle notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Voir',
                icon: '/static/icons/checkmark.png'
            },
            {
                action: 'close',
                title: 'Fermer',
                icon: '/static/icons/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Marketplace', options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Sync cart when back online
async function syncCart() {
    try {
        // Get offline cart from IndexedDB
        const offlineCart = await getOfflineCart();
        
        if (offlineCart && offlineCart.length > 0) {
            // Sync each cart item
            for (const item of offlineCart) {
                try {
                    await fetch('/clients/api/panier/ajouter/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify(item)
                    });
                } catch (error) {
                    console.error('Failed to sync cart item:', error);
                }
            }
            
            // Clear offline cart
            await clearOfflineCart();
        }
    } catch (error) {
        console.error('Cart sync failed:', error);
    }
}

// Sync orders when back online
async function syncOrders() {
    try {
        // Get offline orders from IndexedDB
        const offlineOrders = await getOfflineOrders();
        
        if (offlineOrders && offlineOrders.length > 0) {
            // Sync each order
            for (const order of offlineOrders) {
                try {
                    await fetch('/clients/api/commandes/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify(order)
                    });
                } catch (error) {
                    console.error('Failed to sync order:', error);
                }
            }
            
            // Clear offline orders
            await clearOfflineOrders();
        }
    } catch (error) {
        console.error('Order sync failed:', error);
    }
}

// IndexedDB helpers for offline storage
async function getOfflineCart() {
    // Implementation would use IndexedDB to store cart items
    return [];
}

async function clearOfflineCart() {
    // Clear offline cart from IndexedDB
}

async function getOfflineOrders() {
    // Implementation would use IndexedDB to store orders
    return [];
}

async function clearOfflineOrders() {
    // Clear offline orders from IndexedDB
}

// Cache management
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'CACHE_UPDATE') {
        // Update specific cache
        caches.open(DYNAMIC_CACHE).then(cache => {
            return cache.add(event.data.url);
        });
    }
});