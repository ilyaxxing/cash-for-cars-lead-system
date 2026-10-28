// The seller form and the dashboard behave like apps: the page itself does
// not zoom with two fingers or a double tap. Photos zoom inside the photo
// viewer instead (elements marked data-zoomable handle their own gestures).
//
// The viewport tag (user-scalable=no) is enough for Android, but iPhone
// Safari ignores it, so its pinch gesture events are cancelled here, and
// touch-action: manipulation in base.css removes double-tap zoom.

export function preventPageZoom(): void {
  const cancel = (event: Event) => event.preventDefault()
  for (const type of ['gesturestart', 'gesturechange', 'gestureend']) {
    document.addEventListener(type, cancel, { passive: false })
  }
  document.addEventListener(
    'touchmove',
    (event) => {
      if (event.touches.length < 2) return
      const target = event.target instanceof Element ? event.target : null
      if (!target?.closest('[data-zoomable]')) event.preventDefault()
    },
    { passive: false },
  )
}
