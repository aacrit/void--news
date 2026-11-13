// void --news Service Worker
// Enables offline reading, asset caching, and background sync

// Bump these on any deploy that must invalidate cached shells/assets. The
// activate handler below deletes every cache whose name is not in this set,
// so a version bump purges the previous deploy's cached bundle. Paired with
// the `no-cache` header on /sw.js (see public/_headers), a new SW is picked
// up on the next load instead of after the browser's 24h update check.
const CACHE_NAME = 'void-news-v6';
const ASSET_CACHE = 'void-news-assets-v6';
const API_CACHE = 'void-news-api-v6';

const OFFLINE_URL = '/offline.html';

const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  OFFLINE_URL,
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

// Rate-limit relief (2026-10-03). The edge answers 429 when one reader asks
// for too much too fast: thirteen quick page views made ~330 requests and
// 27 came back 429, and the reader saw Cloudflare's error page several times.
// Three things here keep a busy reader off that page:
//   1. Only a navigation revalidates past the HTTP cache, and it does so with
//      'no-cache' (a conditional request) rather than 'reload'. Data, RSC
//      payloads and audio used to take the 'reload' path too, so every click
//      re-downloaded what the browser already held.
//   2. A 429 or 503 waits (Retry-After, capped) and retries ONCE. Images do
//      not retry: the Sources page alone shows ~900 outlet logos, and
//      doubling those while the edge is refusing keeps the limit tripped.
//      A missing logo is cosmetic; a page, its data and its code are not.
//   3. A navigation that is still refused shows the cached copy of that page,
//      or a short page that retries itself, never the edge's error page.
const RETRY_STATUSES = [429, 503];
const RETRY_CAP_MS = 3000;
const RETRY_DEFAULT_MS = 1500;

function retryDelay(response) {
  const s = Number(response.headers.get('Retry-After'));
  return Number.isFinite(s) && s > 0 ? Math.min(s * 1000, RETRY_CAP_MS) : RETRY_DEFAULT_MS;
}

async function politeFetch(request, init, retry = true) {
  const response = await fetch(request, init);
  if (!retry || !RETRY_STATUSES.includes(response.status)) return response;
  await new Promise((r) => setTimeout(r, retryDelay(response)));
  return fetch(request, init);
}

// Cache.put refuses partial (206) responses, which audio range requests get.
function cacheable(response) {
  return response.status === 200 && response.type === 'basic';
}

const BUSY_PAGE =
  '<!doctype html><html lang="en"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<meta http-equiv="refresh" content="4"><title>One moment | Void News</title>' +
  '<style>body{font-family:Georgia,serif;background:#f4efe6;color:#1a1a1a;display:grid;' +
  'place-items:center;min-height:100vh;margin:0;padding:16px;text-align:center}' +
  '@media (prefers-color-scheme:dark){body{background:#141414;color:#e8e2d6}}</style></head>' +
  '<body><main><h1>One moment.</h1><p>Too many pages at once. This one loads again in a few seconds.</p>' +
  '</main></body></html>';

function busyResponse() {
  return new Response(BUSY_PAGE, {
    status: 503,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Retry-After': '4' },
  });
}

// Fetch event: serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, non-same-origin, external APIs
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  const isImage = request.destination === 'image' ||
    /\.(png|svg|ico|jpg|webp)$/.test(url.pathname);

  // Static assets (JS, CSS, fonts, images): cache-first
  if (
    url.pathname.includes('/_next/') ||
    url.pathname.endsWith('.js') ||
    url.pathname.endsWith('.css') ||
    url.pathname.endsWith('.woff2') ||
    url.pathname.endsWith('.png') ||
    url.pathname.endsWith('.svg') ||
    url.pathname.endsWith('.ico') ||
    url.pathname.endsWith('.jpg') ||
    url.pathname.endsWith('.webp')
  ) {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached || politeFetch(request, undefined, !isImage).then((response) => {
          if (cacheable(response)) {
            const copy = response.clone();
            caches.open(ASSET_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        }))
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

  // Navigation requests (HTML pages): network-first, fall back to cached page,
  // then to the offline shell when both network and cache miss.
  const isNavigation =
    request.mode === 'navigate' || request.destination === 'document';

  if (isNavigation) {
    // 'no-cache' still reaches the edge for the freshest shell (so a new
    // deploy is never hidden behind the shell's own max-age), but as a
    // conditional request the edge answers with a 304 when nothing changed.
    event.respondWith(
      politeFetch(request, { cache: 'no-cache' })
        .then(async (response) => {
          if (cacheable(response)) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
            return response;
          }
          if (RETRY_STATUSES.includes(response.status)) {
            return (await caches.match(request)) || busyResponse();
          }
          return response;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          const offline = await caches.match(OFFLINE_URL);
          if (offline) return offline;
          return new Response('Offline', { status: 503 });
        })
    );
    return;
  }

  // Everything else (data JSON, RSC payloads, audio): the browser's own HTTP
  // cache decides, a 429 retries once, and a network failure falls back to a
  // copy kept from an earlier visit.
  event.respondWith(
    politeFetch(request)
      .then(async (response) => {
        if (cacheable(response) && url.pathname.endsWith('.json')) {
          const copy = response.clone();
          caches.open(API_CACHE).then((cache) => cache.put(request, copy));
        }
        if (RETRY_STATUSES.includes(response.status)) {
          return (await caches.match(request)) || response;
        }
        return response;
      })
      .catch(async () => (await caches.match(request)) || new Response('Offline', { status: 503 }))
  );
});
