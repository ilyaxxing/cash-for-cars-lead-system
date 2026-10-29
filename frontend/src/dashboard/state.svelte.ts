// State of the owner dashboard: sign-in, the three screens, the open lead,
// toasts and dialogs. Addresses follow the screen (/app/leads/42,
// /app/stats), so a notification can open a lead directly and the phone's
// back gesture closes it.

import type { AppConfig } from '../shared/config'
import { createPresenter, type Presenter } from '../shared/present'
import * as api from './api'
import { createFormatter, type Formatter } from './format'
import * as push from './push'

export type Screen = 'leads' | 'stats' | 'settings'
// new_password: signed in with the password that was handed over, which has to
// be replaced first.
export type AuthState = 'checking' | 'signed_out' | 'new_password' | 'signed_in' | 'logged_out'

const SCREEN_KEY = 'dashboard-screen'
const ONBOARDED_KEY = 'dashboard-onboarded'
const REFRESH_MS = 60_000
const SEARCH_DELAY_MS = 250

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value)
  } catch {
    // storage blocked: the preference is simply not remembered
  }
}

export interface Toast {
  message: string
  undo?: () => void
}

export class DashboardState {
  readonly config: AppConfig
  readonly present: Presenter
  readonly t
  readonly fmt: Formatter

  auth = $state<AuthState>('checking')
  passwordChangedAt = $state<string | null>(null)
  onboarded = $state(read(ONBOARDED_KEY) === '1')
  screen = $state<Screen>('leads')
  width = $state(1200)

  tab = $state<api.Tab>('new')
  query = $state('')
  leads = $state<api.Card[]>([])
  counts = $state<Record<api.Tab, number>>({ new: 0, in_work: 0, all: 0 })
  hasMore = $state(false)
  loaded = $state(false)

  openId = $state<number | null>(null)
  navIds = $state<number[]>([])
  detail = $state<api.Detail | null>(null)
  lightbox = $state<number | null>(null)
  confirm = $state<api.Status | null>(null)

  toast = $state<Toast | null>(null)
  logoutOpen = $state(false)

  pushStatus = $state<api.PushStatus | null>(null)
  pushPermission = $state<push.Permission>(push.permission())
  // This device has a subscription the server knows about.
  pushOn = $state(false)

  desk = $derived(this.width >= 900)

  private toastTimer: ReturnType<typeof setTimeout> | undefined
  private searchTimer: ReturnType<typeof setTimeout> | undefined
  private refreshTimer: ReturnType<typeof setInterval> | undefined

  constructor(config: AppConfig) {
    this.config = config
    this.present = createPresenter(config)
    this.t = this.present.t
    this.fmt = createFormatter(this.present.numberLocale, config.timezone, {
      today: (time) => this.t('dashboard.time.today', { time }),
      yesterday: (time) => this.t('dashboard.time.yesterday', { time }),
    })
    const remembered = read(SCREEN_KEY)
    if (remembered === 'stats' || remembered === 'settings') this.screen = remembered
  }

  // --- session -----------------------------------------------------------------

  async start() {
    window.addEventListener('popstate', () => this.applyLocation())
    // Messages from the service worker: a tapped notification, a new lead.
    navigator.serviceWorker?.addEventListener('message', (event: MessageEvent) => {
      if (event.data?.type === 'open' && typeof event.data.path === 'string') {
        history.pushState(null, '', event.data.path)
        this.applyLocation()
      }
      if (event.data?.type === 'refresh' && this.auth === 'signed_in') void this.refresh()
    })
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && this.auth === 'signed_in') void this.refresh()
    })
    try {
      const me = await api.me()
      this.passwordChangedAt = me.passwordChangedAt
      if (me.mustChangePassword) {
        this.auth = 'new_password'
        return
      }
      this.auth = 'signed_in'
      this.applyLocation()
      void this.loadPush(true)
      await this.refresh()
      this.refreshTimer = setInterval(() => document.visibilityState === 'visible' && this.refresh(), REFRESH_MS)
    } catch {
      this.auth = 'signed_out'
    }
  }

  async signIn(password: string): Promise<string | null> {
    try {
      await api.login(password)
    } catch (error) {
      return error instanceof api.RequestFailed && error.code ? error.code : 'network'
    }
    this.auth = 'checking'
    await this.start()
    return null
  }

  /** Replace the password that was handed over; then the dashboard opens. */
  async setOwnPassword(next: string): Promise<string | null> {
    try {
      await api.changePassword('', next)
    } catch (error) {
      if (error instanceof api.Unauthorized) {
        this.auth = 'signed_out'
        return null
      }
      return error instanceof api.RequestFailed && error.status === 422 ? (error.code ?? 'failed') : 'failed'
    }
    this.auth = 'checking'
    await this.start()
    return null
  }

  async signOut() {
    this.logoutOpen = false
    try {
      // A signed-out device must stop showing new leads.
      await this.disablePush().catch(() => undefined)
      await api.logout()
    } finally {
      clearInterval(this.refreshTimer)
      this.openId = null
      this.detail = null
      this.auth = 'logged_out'
    }
  }

  finishOnboarding() {
    write(ONBOARDED_KEY, '1')
    this.onboarded = true
  }

  // Any call that finds the session gone sends the owner back to sign in,
  // and one refused for the password handed over (after a reset) to replacing it.
  private async guard<T>(run: () => Promise<T>): Promise<T | undefined> {
    try {
      return await run()
    } catch (error) {
      if (error instanceof api.Unauthorized) {
        this.auth = 'signed_out'
        return undefined
      }
      if (error instanceof api.RequestFailed && error.code === 'password_change_required') {
        this.auth = 'new_password'
        return undefined
      }
      throw error
    }
  }

  // --- navigation --------------------------------------------------------------

  private applyLocation() {
    const path = location.pathname.replace(/\/+$/, '')
    const lead = /^\/app\/leads\/(\d+)$/.exec(path)
    if (lead) {
      this.screen = 'leads'
      void this.open(Number(lead[1]), false)
      return
    }
    this.openId = null
    this.detail = null
    this.lightbox = null
    if (path === '/app/stats') this.screen = 'stats'
    else if (path === '/app/settings') this.screen = 'settings'
    else if (path === '/app/leads') this.screen = 'leads'
  }

  private navigate(path: string) {
    if (location.pathname !== path) history.pushState(null, '', path)
  }

  go(screen: Screen) {
    this.screen = screen
    this.openId = null
    this.detail = null
    write(SCREEN_KEY, screen)
    this.navigate(screen === 'leads' ? '/app/' : `/app/${screen}`)
  }

  // --- leads -------------------------------------------------------------------

  async refresh() {
    await this.loadLeads(true)
    if (this.openId) await this.reloadDetail()
  }

  async loadLeads(reset: boolean) {
    const offset = reset ? 0 : this.leads.length
    const result = await this.guard(() => api.listLeads(this.tab, this.query.trim(), offset))
    if (!result) return
    this.counts = result.counts
    this.leads = reset ? result.leads : [...this.leads, ...result.leads]
    this.hasMore = result.hasMore
    this.loaded = true
  }

  setTab(tab: api.Tab) {
    this.tab = tab
    void this.loadLeads(true)
  }

  setQuery(query: string) {
    this.query = query
    clearTimeout(this.searchTimer)
    this.searchTimer = setTimeout(() => this.loadLeads(true), SEARCH_DELAY_MS)
  }

  async open(id: number, push = true) {
    if (this.openId === null || !this.navIds.includes(id)) this.navIds = this.leads.map((lead) => lead.id)
    this.openId = id
    this.lightbox = null
    if (push) this.navigate(`/app/leads/${id}`)
    await this.reloadDetail()
  }

  private async reloadDetail() {
    const id = this.openId
    if (id === null) return
    try {
      const detail = await this.guard(() => api.getLead(id))
      if (detail && this.openId === id) this.detail = detail
    } catch {
      if (this.openId === id) this.close()
    }
  }

  close() {
    this.openId = null
    this.detail = null
    this.lightbox = null
    this.navigate('/app/')
  }

  step(direction: number) {
    const index = this.navIds.indexOf(this.openId ?? -1)
    const next = this.navIds[index + direction]
    if (index >= 0 && next !== undefined) void this.open(next)
  }

  // --- changes -----------------------------------------------------------------

  flash(message: string, undo?: () => void) {
    clearTimeout(this.toastTimer)
    this.toast = { message, undo }
    this.toastTimer = setTimeout(() => (this.toast = null), 4500)
  }

  statusLabel(status: string): string {
    return this.t(`statuses.${status}`)
  }

  // Purchased and Rejected ask first; the others apply at once with Undo.
  requestStatus(status: api.Status) {
    if (!this.detail || this.detail.status === status) return
    if (status === 'bought' || status === 'rejected') this.confirm = status
    else void this.applyStatus(status)
  }

  async applyStatus(status: api.Status) {
    this.confirm = null
    const lead = this.detail
    if (!lead) return
    const previous = lead.status
    try {
      const result = await this.guard(() => api.setStatus(lead.id, status))
      if (!result) return
      const event = result.event
      const undo =
        event && status !== 'bought' && status !== 'rejected'
          ? async () => {
              this.toast = null
              await this.guard(() => api.setStatus(lead.id, previous, event.id))
              await this.refresh()
            }
          : undefined
      this.flash(this.t('dashboard.toast.moved', { status: this.statusLabel(status) }), undo)
      await this.refresh()
    } catch {
      this.flash(this.t('dashboard.toast.failed'))
    }
  }

  async addNote(text: string): Promise<boolean> {
    const lead = this.detail
    if (!lead || !text.trim()) return false
    try {
      const note = await this.guard(() => api.addNote(lead.id, text))
      if (!note) return false
      this.flash(this.t('dashboard.toast.note_added'))
      await this.reloadDetail()
      return true
    } catch {
      this.flash(this.t('dashboard.toast.failed'))
      return false
    }
  }

  async deleteNote(noteId: number) {
    const lead = this.detail
    if (!lead) return
    try {
      await this.guard(() => api.deleteNote(lead.id, noteId))
      this.flash(this.t('dashboard.toast.note_deleted'), async () => {
        this.toast = null
        await this.guard(() => api.restoreNote(lead.id, noteId))
        await this.reloadDetail()
      })
      await this.reloadDetail()
    } catch {
      this.flash(this.t('dashboard.toast.failed'))
    }
  }

  // --- push notifications ------------------------------------------------------

  async loadPush(resync = false) {
    this.pushPermission = push.permission()
    try {
      const subscription = await push.currentSubscription()
      // On start, re-register a subscription the server lost (device removed
      // after failures, database restored) before reading the status.
      if (resync && subscription) await api.savePushSubscription(subscription.toJSON())
      this.pushStatus = (await this.guard(() => api.pushStatus())) ?? null
      this.pushOn = Boolean(subscription)
    } catch {
      // Status is informational; the dashboard works without it.
    }
  }

  async enablePush(): Promise<'ok' | 'denied' | 'failed'> {
    const key = this.pushStatus?.publicKey
    if (!key) return 'failed'
    try {
      const result = await push.subscribe(key)
      this.pushPermission = push.permission()
      if (result === 'denied') return 'denied'
      await this.guard(() => api.savePushSubscription(result.toJSON()))
      this.pushOn = true
      await this.loadPush()
      return 'ok'
    } catch {
      return 'failed'
    }
  }

  async disablePush() {
    const endpoint = await push.unsubscribe()
    if (endpoint) await this.guard(() => api.removePushSubscription(endpoint))
    this.pushOn = false
    await this.loadPush()
  }

  async testPush(): Promise<'ok' | 'permission' | 'failed'> {
    if (push.permission() !== 'granted') return 'permission'
    try {
      const subscription = await push.currentSubscription()
      const result = await this.guard(() => api.sendTestPush(subscription?.endpoint))
      await this.loadPush()
      return result && result.delivered > 0 ? 'ok' : 'failed'
    } catch {
      return 'failed'
    }
  }

  async changePassword(current: string, next: string): Promise<string | null> {
    try {
      await this.guard(() => api.changePassword(current, next))
      this.passwordChangedAt = new Date().toISOString()
      return null
    } catch (error) {
      return error instanceof api.RequestFailed && error.status === 422 ? (error.code ?? 'failed') : 'failed'
    }
  }
}
