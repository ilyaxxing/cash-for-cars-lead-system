// Service worker of the owner dashboard (scope /app/).
//
// Shows push notifications about new leads and opens the lead when one is
// tapped. Keeps the app shell available offline so the installed app opens
// even on a bad connection. API responses are never cached: they carry
// sellers' personal data and must always be fresh.

const SHELL_CACHE = 'dashboard-shell-v1'
const SHELL_URL = '/app/'

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.add(SHELL_URL))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== SHELL_CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return

  if (request.mode === 'navigate') {
    // Network first, so a new deploy shows up at once; the cached shell
    // only when offline.
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(SHELL_CACHE).then((cache) => cache.put(SHELL_URL, copy))
          return response
        })
        .catch(() => caches.match(SHELL_URL)),
    )
    return
  }

  if (url.pathname.startsWith('/assets/')) {
    // Hashed bundle files never change: cache on first use.
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const copy = response.clone()
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy))
            return response
          }),
      ),
    )
  }
})

// --- push notifications ----------------------------------------------------

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch {
    data = { title: event.data ? event.data.text() : '' }
  }
  const show = self.registration.showNotification(data.title || 'New lead', {
    body: data.body || '',
    tag: data.tag,
    renotify: Boolean(data.tag),
    icon: '/app/icons/icon-192.png',
    badge: '/app/icons/badge-96.png',
    data: { url: data.url || '/app/' },
  })
  // Open dashboards refresh their list without waiting for the next poll.
  const refresh = self.clients
    .matchAll({ type: 'window', includeUncontrolled: true })
    .then((windows) => windows.forEach((client) => client.postMessage({ type: 'refresh' })))
  event.waitUntil(Promise.all([show, refresh]))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL(event.notification.data?.url || '/app/', self.location.origin)
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (windows) => {
      const open = windows.find((client) => new URL(client.url).pathname.startsWith('/app'))
      if (open) {
        // Navigation inside the running app; iOS does not support client.navigate().
        open.postMessage({ type: 'open', path: target.pathname })
        return open.focus()
      }
      return self.clients.openWindow(target.href)
    }),
  )
})
