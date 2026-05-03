// void --news Service Worker
// Enables offline reading, asset caching, and background sync

const CACHE_NAME = 'void-news-v1';
const ASSET_CACHE = 'void-news-assets-v1';
const API_CACHE = 'void-news-api-v1';

const PRECACHE_ASSETS = [
  '/void--news/',
  '/void--news/manifest.json',
  '/void--news/icon-192.png',
  '/void--news/icon-512.png',
];

// Install event: precache core assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Service Worker: precaching core assets');
      return cache.addAll(PRECACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate event: clean up old cache versions
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME && name !== ASSET_CACHE && name !== API_CACHE) {
            console.log(`Service Worker: deleting old cache ${name}`);
            return caches.delete(name);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event: serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, non-same-origin, external APIs
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // API calls: network-first, fallback to cache
  if (url.pathname.includes('/api/') || url.pathname.includes('supabase')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            caches.open(API_CACHE).then((cache) => cache.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets (JS, CSS, fonts, images): cache-first
  if (
    url.pathname.includes('/_next/') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.svg')
  ) {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached || fetch(request))
        .then((response) => {
          if (response.ok) {
            caches.open(ASSET_CACHE).then((cache) => cache.put(request, response.clone()));
          }
          return response;
        })
        .catch(() => {
          // Fallback offline response for assets
          if (request.destination === 'image') {
            return new Response('<svg></svg>', { headers: { 'Content-Type': 'image/svg+xml' } });
          }
          return new Response('Offline', { status: 503 });
        })
    );
    return;
  }

  // HTML pages: network-first, fallback to cache
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          caches.open(CACHE_NAME).then((cache) => cache.put(request, response.clone()));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
