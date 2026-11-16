// Minimaler Service Worker: macht die App auf Android installierbar.
// Er speichert bewusst nichts zwischen, damit Updates sofort ankommen.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.mode === 'navigate') e.respondWith(fetch(e.request));
});
