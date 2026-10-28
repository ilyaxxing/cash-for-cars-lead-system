// Web Push on this device: permission, subscription, and the iPhone rule
// that only home-screen apps may receive notifications.

export type Permission = 'granted' | 'default' | 'denied' | 'unsupported' | 'ios_home' | 'insecure'

function isStandalone(): boolean {
  return (
    window.matchMedia?.('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  )
}

function isIos(): boolean {
  const agent = navigator.userAgent
  return /iPhone|iPad|iPod/.test(agent) || (agent.includes('Mac') && navigator.maxTouchPoints > 1)
}

export function permission(): Permission {
  // Browsers offer push only on https (and localhost). Opened over plain
  // http, say so, rather than blame the browser.
  if (!window.isSecureContext) return 'insecure'
  const supported = 'serviceWorker' in navigator && 'PushManager' in window && typeof Notification !== 'undefined'
  if (!supported) return isIos() && !isStandalone() ? 'ios_home' : 'unsupported'
  return Notification.permission as Permission
}

async function registration(): Promise<ServiceWorkerRegistration> {
  return navigator.serviceWorker.ready
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (permission() !== 'granted') return null
  return (await registration()).pushManager.getSubscription()
}

function keyBytes(base64url: string): Uint8Array<ArrayBuffer> {
  const base64 = (base64url + '='.repeat((4 - (base64url.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const bytes = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i)
  return bytes
}

// Must run from a tap: browsers only show the permission prompt then.
export async function subscribe(publicKey: string): Promise<PushSubscription | 'denied'> {
  const answer = await Notification.requestPermission()
  if (answer !== 'granted') return 'denied'
  const reg = await registration()
  const existing = await reg.pushManager.getSubscription()
  if (existing) return existing
  return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(publicKey) })
}

export async function unsubscribe(): Promise<string | null> {
  const subscription = await currentSubscription()
  if (!subscription) return null
  const endpoint = subscription.endpoint
  await subscription.unsubscribe()
  return endpoint
}
