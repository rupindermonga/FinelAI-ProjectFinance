// Finel AI Project Finance — Service Worker
// Strategy: network-first for API calls, cache-first for static assets

const CACHE = 'finel-pf-v1';
const STATIC = [
  '/static/css/style.css',
  '/static/js/app-2.js',
  '/static/favicon.svg',
  '/static/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Network-first for API calls — never cache
  if (url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Cache-first for static assets
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const fresh = fetch(e.request).then(res => {
          if (res.ok) caches.open(CACHE).then(c => c.put(e.request, res.clone()));
          return res;
        });
        return cached || fresh;
      })
    );
    return;
  }

  // Network-first for HTML pages
  e.respondWith(
    fetch(e.request).catch(() => caches.match('/'))
  );
});
