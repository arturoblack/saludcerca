/* Service worker de SaludCerca.
 * - La "cáscara" de la app (HTML, JS, CSS, íconos) se guarda para abrirla sin señal.
 * - /api/citas, /api/medicos y /api/me: primero red y, si no hay, la última respuesta guardada.
 * - Las historias clínicas NO se guardan en el dispositivo (tabletas compartidas en el puesto de salud).
 */
const CACHE = 'saludcerca-v1';
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/icon.svg', '/icon-192.png'];
const API_OFFLINE = ['/api/citas', '/api/medicos', '/api/me'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (url.pathname.startsWith('/api/')) {
    if (!API_OFFLINE.includes(url.pathname)) return; // nada clínico en caché
    e.respondWith(fetch(e.request).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
      return res;
    }).catch(() => caches.match(e.request).then((r) => r || (url.pathname === '/api/me'
      ? new Response('{"error":"Sin conexión"}', { status: 503, headers: { 'Content-Type': 'application/json' } })
      : new Response('[]', { headers: { 'Content-Type': 'application/json' } })))));
    return;
  }

  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match('/index.html')));
    return;
  }
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request).then((res) => {
    if (res.ok && url.pathname.startsWith('/assets/')) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
    return res;
  })));
});
