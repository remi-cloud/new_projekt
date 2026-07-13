self.addEventListener('push', (event) => {
  let data = { title: 'Cyclical Trader', body: 'Nowy sygnał rynkowy' }
  try {
    if (event.data) data = event.data.json()
  } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title || 'Cyclical Trader', {
      body: data.body || '',
      icon: '/manifest.json',
      badge: '/manifest.json',
      data: { symbol: data.symbol, url: data.symbol ? `/instrument/${encodeURIComponent(data.symbol)}` : '/' },
      tag: data.symbol || 'cyclical-alert',
      renotify: true,
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(clients.openWindow(url))
})
