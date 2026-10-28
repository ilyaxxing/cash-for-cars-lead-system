// Wires the demo backend into a page before the app starts: fetch and
// XMLHttpRequest calls to /api go to it, the service worker and push
// permission are stood in for, and a notification shows as a banner inside
// the dashboard. The form and the dashboard on the project page run in two
// frames of one page; they share the leads through the top window and pass
// notifications over a BroadcastChannel. A demo link can name the business
// it is shown to (?name=Rapid+Cash+Cars&color=ff8a00): the apps and the
// policy then wear that name and color, as that business's instance would.

import type { Value } from '../form/engine'
import type { AppConfig } from '../shared/config'
import { normalizePhone } from '../shared/region'
import { Backend, type DemoData, type Notice, type Reply } from './backend'
import { business, wear, type Business } from './business'
import { seed } from './seed'

const CHANNEL = 'car-buyout-demo'
const STORE = '__carBuyoutDemo'
// Drafts and preferences the real apps keep in localStorage; a demo starts clean.
const FORM_DRAFT = 'car-buyout-inquiry'
const ONBOARDED = 'dashboard-onboarded'
const LATENCY_MS = 180
// The fictional business tools/make_demo.py builds the pages for.
const DEMO_NAMES = ['Example Auto LLC', 'Car Buyout']

type Host = Window & { [STORE]?: DemoData }

function host(): Host {
  try {
    // Same origin on the project page; a page opened on its own is its own host.
    void window.top?.location.href
    return (window.top ?? window) as Host
  } catch {
    return window as Host
  }
}

function sharedData(): DemoData {
  const top = host()
  top[STORE] ??= seed(new Date())
  return top[STORE]
}

function storage(action: (store: Storage) => void) {
  try {
    action(localStorage)
  } catch {
    // storage blocked: the demo still works, it only forgets
  }
}

function readConfig(visitor: Business): AppConfig {
  const block = document.getElementById('app-config')!
  const config = JSON.parse(block.textContent!) as AppConfig
  if (visitor.name) {
    config.brand = { ...config.brand, name: visitor.name, logo: null }
    // The consent text names the business that receives the data.
    config.operator = visitor.name
  }
  if (visitor.colors) wear(visitor.colors)
  // The policy sits next to the demo pages. An absolute address keeps the
  // link working after the dashboard changes its path (/app/leads/42).
  config.privacyUrl = new URL(/* @vite-ignore */ `../privacy.html${visitor.query}`, import.meta.url).href
  block.textContent = JSON.stringify(config)
  return config
}

// The policy page is plain HTML from the server: put the business's name
// where the demo business's stands, and its color on the mark and links.
export function personalizePolicy() {
  const visitor = business()
  if (visitor.colors) wear(visitor.colors)
  const back = document.querySelector<HTMLAnchorElement>('header a')
  if (back) back.href = `index.html${visitor.query}`
  if (!visitor.name) return
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    let text = node.nodeValue ?? ''
    for (const demo of DEMO_NAMES) text = text.split(demo).join(visitor.name)
    node.nodeValue = text
  }
  document.title = document.title.split(DEMO_NAMES[1]).join(visitor.name)
}

function respond(reply: Reply): Response {
  if (reply.body === undefined) return new Response(null, { status: reply.status })
  return new Response(JSON.stringify(reply.body), {
    status: reply.status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const pause = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

function routeFetch(backend: Backend) {
  const original = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const raw = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const url = new URL(raw, location.href)
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) return original(input, init)
    const method = (init?.method ?? (input instanceof Request ? input.method : 'GET')).toUpperCase()
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined
    await pause(LATENCY_MS)
    return respond(backend.handle(method, url.pathname + url.search, body))
  }
}

// The form uploads photos with XMLHttpRequest for its progress bar. The
// photo stays in this browser as a blob: URL; the dashboard frame on the
// same page can show it.
function routeUploads(backend: Backend) {
  class DemoRequest {
    upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null }
    onload: (() => void) | null = null
    onerror: (() => void) | null = null
    status = 0
    responseText = ''
    private url = ''

    open(_method: string, url: string) {
      this.url = url
    }

    setRequestHeader() {}

    send(form: FormData) {
      const file = form.get('file')
      const slot = form.get('slot')
      const lead = /\/api\/leads\/(\d+)\/photos$/.exec(this.url)
      if (!(file instanceof Blob) || !lead) {
        setTimeout(() => this.onerror?.(), 0)
        return
      }
      const steps = 6
      for (let step = 1; step <= steps; step++) {
        setTimeout(() => {
          const progress = { lengthComputable: true, loaded: (file.size * step) / steps, total: file.size }
          this.upload.onprogress?.(progress as ProgressEvent)
          if (step < steps) return
          const address = URL.createObjectURL(file)
          const reply = backend.addPhoto(Number(lead[1]), typeof slot === 'string' ? slot : null, address, address)
          this.status = reply.status
          this.responseText = JSON.stringify(reply.body ?? {})
          this.onload?.()
        }, step * 120)
      }
    }
  }
  window.XMLHttpRequest = DemoRequest as unknown as typeof XMLHttpRequest
}

// Push on this "device": permission granted, one subscription, and a worker
// whose messages the dashboard already listens to (refresh, open a lead).
function standInForPush(data: DemoData) {
  const listeners = new Set<(event: MessageEvent) => void>()
  const endpoint = 'https://push.invalid/demo'
  const subscription = {
    endpoint,
    toJSON: () => ({ endpoint, keys: { p256dh: 'demo', auth: 'demo' } }),
    unsubscribe: async () => {
      data.pushOn = false
      return true
    },
  }
  const registration = {
    pushManager: {
      getSubscription: async () => (data.pushOn ? subscription : null),
      subscribe: async () => {
        data.pushOn = true
        return subscription
      },
    },
  }
  const worker = {
    ready: Promise.resolve(registration),
    register: async () => registration,
    addEventListener: (type: string, listener: (event: MessageEvent) => void) => {
      if (type === 'message') listeners.add(listener)
    },
    removeEventListener: (_type: string, listener: (event: MessageEvent) => void) => listeners.delete(listener),
  }
  Object.defineProperty(navigator, 'serviceWorker', { value: worker, configurable: true })
  const scope = window as unknown as Record<string, unknown>
  // iPhone Safari offers push only to home-screen apps; the demo is not one.
  scope.PushManager ??= class {}
  if (typeof Notification === 'undefined') {
    scope.Notification = { permission: 'granted', requestPermission: async () => 'granted' }
  } else {
    Object.defineProperty(Notification, 'permission', { get: () => 'granted', configurable: true })
    Notification.requestPermission = async () => 'granted'
  }
  return (data: unknown) => {
    for (const listener of listeners) listener(new MessageEvent('message', { data }))
  }
}

function showBanner(notice: Notice, post: (data: unknown) => void) {
  document.querySelector('.demo-banner')?.remove()
  const banner = document.createElement('button')
  banner.type = 'button'
  banner.className = 'demo-banner'
  banner.innerHTML = `
    <span class="demo-banner-mark"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6.8v4.6c0 .5.2 1 .6 1.4l6.1 6.1c.8.8 2 .8 2.8 0l4.1-4.1c.8-.8.8-2 0-2.8l-6.1-6.1c-.4-.4-.9-.6-1.4-.6H6.8C5.8 5.3 5 6 5 6.8z" fill="var(--on-accent)"/><circle cx="8.4" cy="8.6" r="1.3" fill="var(--accent)"/></svg></span>
    <span class="demo-banner-text"><b></b><span></span></span>
    <span class="demo-banner-time">now</span>`
  banner.querySelector('b')!.textContent = notice.title
  banner.querySelector('.demo-banner-text span')!.textContent = notice.body
  banner.addEventListener('click', () => {
    banner.remove()
    post({ type: 'open', path: notice.path })
  })
  document.body.append(banner)
  setTimeout(() => banner.classList.add('shown'), 20)
  setTimeout(() => {
    banner.classList.remove('shown')
    setTimeout(() => banner.remove(), 400)
  }, 12000)
}

const BANNER_STYLE = `
.demo-banner{position:fixed;z-index:1000;top:10px;left:10px;right:10px;display:flex;gap:12px;
align-items:center;padding:12px 14px;border:0;border-radius:20px;text-align:left;cursor:pointer;
background:rgb(46 48 48 / .92);-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px);
color:var(--text);font:inherit;box-shadow:0 12px 40px rgb(0 0 0 / .45);
transform:translateY(-130%);transition:transform .35s var(--ease-out)}
.demo-banner.shown{transform:none}
.demo-banner-mark{flex:none;width:38px;height:38px;padding:7px;border-radius:10px;background:var(--accent)}
.demo-banner-mark svg{display:block;width:100%;height:100%}
.demo-banner-text{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;font-size:14px;line-height:1.3}
.demo-banner-text b{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.demo-banner-text span{color:var(--text-soft)}
.demo-banner-time{align-self:flex-start;color:var(--text-muted);font-size:12px}`

export function install() {
  const config = readConfig(business())
  const data = sharedData()
  const isDashboard = location.pathname.includes('/app/')
  const channel = new BroadcastChannel(CHANNEL)
  let post: (data: unknown) => void = () => {}

  const announce = (notice: Notice) => {
    channel.postMessage(notice)
    // A test push from the dashboard itself never comes back over the channel.
    if (isDashboard) showBanner(notice, post)
  }
  const normalize = (answers: Record<string, Value>) =>
    typeof answers.phone === 'string' ? { ...answers, phone: normalizePhone(answers.phone) ?? answers.phone } : answers
  const backend = new Backend(data, config, announce, normalize)
  routeFetch(backend)

  if (isDashboard) {
    storage((store) => store.setItem(ONBOARDED, '1'))
    post = standInForPush(data)
    const style = document.createElement('style')
    style.textContent = BANNER_STYLE
    document.head.append(style)
    channel.addEventListener('message', (event: MessageEvent<Notice>) => {
      post({ type: 'refresh' })
      showBanner(event.data, post)
    })
  } else {
    storage((store) => store.removeItem(FORM_DRAFT))
    routeUploads(backend)
  }
}
