/* void --news — Service Worker
   Cache strategy:
   - Navigation: network-first, fallback to cache
   - Static assets (CSS/JS/fonts/images): cache-first, fallback to network
   - Supabase API (*.supabase.co): network-first with 5s timeout, fallback to cache
   - Audio files: never cached (too large)
*/

const CACHE_VERSION = 'void-news-v2';

const APP_SHELL = [
  '/void--news/',
  '/void--news/index.html',
  '/',
];

/* ---- Install: precache app shell ---------------------------------------- */

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_VERSION).then(function(cache) {
      return cache.addAll(APP_SHELL).catch(function() {
        // Partial failure is acceptable — the shell may not all be available
        // at install time on first deploy. Continue install regardless.
      });
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

/* ---- Activate: clean up old cache versions ------------------------------ */

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames
          .filter(function(name) { return name !== CACHE_VERSION; })
          .map(function(name) { return caches.delete(name); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

/* ---- Fetch: routing strategy -------------------------------------------- */

self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  // Never cache audio files — too large, streaming is handled by the browser
  if (isAudioRequest(url)) {
    return; // fall through to native network fetch
  }

  // Supabase API requests — network-first with 5s timeout, fallback to cache
  if (isSupabaseRequest(url)) {
    event.respondWith(networkFirstWithTimeout(event.request, 5000));
    return;
  }

  // Navigation requests — network-first, fallback to cached app shell
  if (event.request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(event.request));
    return;
  }

  // Static assets — cache-first, fallback to network
  if (isStaticAsset(url)) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // All other requests — network only (no caching)
});

/* ---- Strategy helpers --------------------------------------------------- */

function isAudioRequest(url) {
  return (
    url.pathname.endsWith('.mp3') ||
    url.pathname.endsWith('.wav') ||
    url.pathname.endsWith('.ogg') ||
    url.pathname.endsWith('.aac') ||
    url.hostname.includes('storage.googleapis.com') && url.pathname.includes('audio')
  );
}

function isSupabaseRequest(url) {
  return url.hostname.endsWith('.supabase.co');
}

function isStaticAsset(url) {
  var ext = url.pathname.split('.').pop().toLowerCase();
  return (
    ['css', 'js', 'woff', 'woff2', 'ttf', 'otf', 'png', 'jpg', 'jpeg', 'svg', 'ico', 'webp', 'gif'].indexOf(ext) !== -1 ||
    url.pathname.startsWith('/_next/static/')
  );
}

/* Cache-first: serve from cache, fetch and cache on miss */
function cacheFirst(request) {
  return caches.open(CACHE_VERSION).then(function(cache) {
    return cache.match(request).then(function(cached) {
      if (cached) return cached;
      return fetch(request).then(function(response) {
        if (response && response.status === 200 && response.type !== 'opaque') {
          cache.put(request, response.clone());
        }
        return response;
      });
    });
  });
}

/* Network-first for navigation: try network, fall back to cached shell */
function networkFirstNavigation(request) {
  return fetch(request).then(function(response) {
    return caches.open(CACHE_VERSION).then(function(cache) {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
      return response;
    });
  }).catch(function() {
    return caches.open(CACHE_VERSION).then(function(cache) {
      // Try the exact URL first, then the app shell root
      return cache.match(request).then(function(cached) {
        if (cached) return cached;
        return cache.match('/void--news/') || cache.match('/');
      });
    });
  });
}

/* Network-first with timeout: race network against a timeout,
   fall back to cache if the network is slow or unavailable */
function networkFirstWithTimeout(request, timeoutMs) {
  return new Promise(function(resolve, reject) {
    var didTimeout = false;
    var timeoutId = setTimeout(function() {
      didTimeout = true;
      caches.open(CACHE_VERSION).then(function(cache) {
        return cache.match(request);
      }).then(function(cached) {
        if (cached) {
          resolve(cached);
        } else {
          // No cache — let the in-flight request resolve even if slow
          // (reject is never called here; the fetch promise wins)
        }
      });
    }, timeoutMs);

    fetch(request).then(function(response) {
      clearTimeout(timeoutId);
      if (!didTimeout) {
        caches.open(CACHE_VERSION).then(function(cache) {
          if (response && response.status === 200) {
            cache.put(request, response.clone());
          }
        });
        resolve(response);
      }
    }).catch(function() {
      clearTimeout(timeoutId);
      caches.open(CACHE_VERSION).then(function(cache) {
        return cache.match(request);
      }).then(function(cached) {
        if (cached) {
          resolve(cached);
        } else {
          reject(new Error('Network unavailable and no cache for: ' + request.url));
        }
      });
    });
  });
}
