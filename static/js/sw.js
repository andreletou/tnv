// Service Worker for Local-Links PWA

const CACHE_NAME = 'Local-links-togo-v1';
const STATIC_CACHE_NAME = 'Local-links-static-v1';
const DYNAMIC_CACHE_NAME = 'Local-links-dynamic-v1';

const STATIC_ASSETS = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/js/api.js',
    '/static/js/cart.js',
    '/static/js/favorites.js',
    '/static/manifest.json',
    '/static/images/icons/icon-192x192.png',
    '/static/images/icons/icon-512x512.png',
    'https://cdn.tailwindcss.com',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('Service Worker: Static assets cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Failed to cache static assets', error);
            })
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
                        if (cacheName !== STATIC_CACHE_NAME && 
                            cacheName !== DYNAMIC_CACHE_NAME &&
                            cacheName !== CACHE_NAME) {
                            console.log('Service Worker: Deleting old cache', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('Service Worker: Activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip external requests (except CDN)
    if (url.origin !== location.origin && 
        !url.hostname.includes('cdn.tailwindcss.com') &&
        !url.hostname.includes('cdnjs.cloudflare.com')) {
        return;
    }
    
    event.respondWith(
        caches.match(request)
            .then(cachedResponse => {
                // Return cached version if available
                if (cachedResponse) {
                    // For static assets, return from cache
                    if (STATIC_ASSETS.includes(url.pathname) || 
                        url.hostname.includes('cdn.tailwindcss.com') ||
                        url.hostname.includes('cdnjs.cloudflare.com')) {
                        return cachedResponse;
                    }
                    
                    // For dynamic content, try network first, then cache
                    return fetch(request)
                        .then(networkResponse => {
                            // Cache successful network responses
                            if (networkResponse.ok) {
                                const responseClone = networkResponse.clone();
                                caches.open(DYNAMIC_CACHE_NAME)
                                    .then(cache => cache.put(request, responseClone));
                            }
                            return networkResponse;
                        })
                        .catch(() => {
                            // Network failed, return cached version
                            return cachedResponse;
                        });
                }
                
                // Not in cache, try network
                return fetch(request)
                    .then(networkResponse => {
                        // Cache successful responses
                        if (networkResponse.ok) {
                            const responseClone = networkResponse.clone();
                            
                            // Determine cache name based on content type
                            const cacheName = url.pathname.includes('/static/') ? 
                                STATIC_CACHE_NAME : DYNAMIC_CACHE_NAME;
                            
                            caches.open(cacheName)
                                .then(cache => cache.put(request, responseClone));
                        }
                        
                        return networkResponse;
                    })
                    .catch(() => {
                        // Network failed and no cache available
                        // Return offline page for navigation requests
                        if (request.mode === 'navigate') {
                            return caches.match('/offline.html') ||
                                new Response('Offline - Please check your connection', {
                                    status: 503,
                                    statusText: 'Service Unavailable'
                                });
                        }
                        
                        // Return error for other requests
                        return new Response('Network error', {
                            status: 408,
                            statusText: 'Request Timeout'
                        });
                    });
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync', event.tag);
    
    if (event.tag === 'cart-sync') {
        event.waitUntil(syncCart());
    } else if (event.tag === 'favorites-sync') {
        event.waitUntil(syncFavorites());
    }
});

// Push notifications
self.addEventListener('push', event => {
    console.log('Service Worker: Push received');
    
    const options = {
        body: event.data ? event.data.text() : 'Nouvelle notification',
        icon: '/static/images/icons/icon-192x192.png',
        badge: '/static/images/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'Voir',
                icon: '/static/images/icons/checkmark.png'
            },
            {
                action: 'close',
                title: 'Fermer',
                icon: '/static/images/icons/xmark.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('Local-Links', options)
    );
});

// Notification click
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification click received');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        // Open the app to relevant page
        event.waitUntil(
            clients.openWindow('/')
        );
    } else if (event.action === 'close') {
        // Just close the notification
        event.notification.close();
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Periodic background sync
self.addEventListener('periodicsync', event => {
    console.log('Service Worker: Periodic sync', event.tag);
    
    if (event.tag === 'update-cache') {
        event.waitUntil(updateCache());
    }
});

// Helper functions
async function syncCart() {
    try {
        // Sync cart items with server
        const cart = await getStoredData('Local-links_cart');
        if (cart && cart.items.length > 0) {
            // Send cart data to server
            await fetch('/clients/api/panier/sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(cart)
            });
        }
    } catch (error) {
        console.error('Cart sync failed:', error);
    }
}

async function syncFavorites() {
    try {
        // Sync favorites with server
        const favorites = await getStoredData('Local-links_favorites');
        if (favorites && favorites.length > 0) {
            // Send favorites data to server
            await fetch('/clients/api/favoris/sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ favorites })
            });
        }
    } catch (error) {
        console.error('Favorites sync failed:', error);
    }
}

async function updateCache() {
    try {
        // Update dynamic cache with fresh content
        const cache = await caches.open(DYNAMIC_CACHE_NAME);
        const urls = [
            '/clients/accueil/',
            '/clients/liste_boutiques/',
            '/clients/api/produits/suggestions/'
        ];
        
        for (const url of urls) {
            try {
                const response = await fetch(url);
                if (response.ok) {
                    await cache.put(url, response);
                }
            } catch (error) {
                console.error(`Failed to update cache for ${url}:`, error);
            }
        }
    } catch (error) {
        console.error('Cache update failed:', error);
    }
}

async function getStoredData(key) {
    return new Promise((resolve, reject) => {
        // In a real implementation, you'd use IndexedDB
        // For now, return null
        resolve(null);
    });
}

// Cache cleanup
async function cleanupCache() {
    const cacheNames = await caches.keys();
    const oldCaches = cacheNames.filter(name => 
        name !== STATIC_CACHE_NAME && 
        name !== DYNAMIC_CACHE_NAME
    );
    
    await Promise.all(
        oldCaches.map(name => caches.delete(name))
    );
}

// Message handling
self.addEventListener('message', event => {
    console.log('Service Worker: Message received', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data && event.data.type === 'CACHE_UPDATED') {
        // Notify clients about cache update
        self.clients.matchAll().then(clients => {
            clients.forEach(client => {
                client.postMessage({
                    type: 'CACHE_UPDATED',
                    url: event.data.url
                });
            });
        });
    }
});