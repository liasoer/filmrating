// Service Worker: macht die App installierbar und empfängt Push-Mitteilungen.
// Er speichert bewusst nichts zwischen, damit Updates sofort ankommen.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode === 'navigate') e.respondWith(fetch(e.request));
});

self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || 'Screenreview', {
    body: d.body || '',
    icon: 'icon-192.png?v=4',
    badge: 'icon-192.png?v=4',
    tag: 'freunde',
    data: { url: d.url || './' }
  }));
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const raw = (e.notification.data && e.notification.data.url || './').replace(/^\/filmrating\//, './');
  const url = new URL(raw, self.registration.scope).href;
  e.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    for (const c of all) { if ('focus' in c) { c.postMessage({ type: 'open-profile', url }); return c.focus(); } }
    return self.clients.openWindow(url);
  })());
});
