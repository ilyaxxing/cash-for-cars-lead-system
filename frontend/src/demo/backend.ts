// A stand-in for the server, run in the browser by the live demo on the
// project page (docs/demo, built by tools/make_demo.py). The real form and
// dashboard call it instead of the API, so a visitor can try both and
// nothing they type leaves the page. It answers in the API's shapes (the
// types come from the API modules) and follows the server's rules where a
// visitor would notice: tabs, search, statuses with undo, notes, statistics.

import type { Card, Detail, LeadEvent, LeadList, Note, Photo, PushStatus, Stats, Status, Tab } from '../dashboard/api'
import type { Value } from '../form/engine'
import type { StoredLead } from '../form/api'
import type { AppConfig, FieldSpec } from '../shared/config'
import { createTranslator } from '../shared/i18n'

export interface DemoPhoto {
  id: number
  slot: string | null
  thumb: string
  full: string
}

export interface DemoNote extends Note {
  deleted: boolean
}

export interface DemoLead {
  id: number
  status: Status
  createdAt: string
  submittedAt: string | null
  statusChangedAt: string
  closedAt: string | null
  source: string
  answers: Record<string, Value>
  photos: DemoPhoto[]
  notes: DemoNote[]
  events: LeadEvent[]
}

export interface DemoData {
  leads: DemoLead[]
  // One counter for leads, photos, notes and events: ids only need to be unique.
  nextId: number
  signedIn: boolean
  pushOn: boolean
}

// What the server would send to the owner's phone.
export interface Notice {
  title: string
  body: string
  path: string
}

export interface Reply {
  status: number
  body?: unknown
}

export const PAGE_SIZE = 60
const NOTE_MAX_LENGTH = 1000
const CLOSED: Status[] = ['bought', 'rejected']
const STATUSES: Status[] = ['new', 'in_work', 'bought', 'rejected']
const TABS: Record<Tab, Status[] | null> = { new: ['new'], in_work: ['in_work'], all: null }
// The demo business's own placements (SOURCE_LABELS on a real instance).
export const SOURCE_LABELS: Record<string, string> = { parking: 'Parking lot', flyer: 'Flyers' }

type Handler = (match: RegExpMatchArray, query: URLSearchParams, body: Record<string, unknown>) => Reply

export class Backend {
  private readonly t
  private readonly money: Intl.NumberFormat
  private readonly personal: Set<string>
  private readonly slotOrder: string[]
  private readonly routes: [string, RegExp, Handler][]

  constructor(
    private readonly data: DemoData,
    private readonly config: AppConfig,
    private readonly notify: (notice: Notice) => void,
    private readonly normalize: (answers: Record<string, Value>) => Record<string, Value> = (a) => a,
    private readonly now: () => Date = () => new Date(),
  ) {
    this.t = createTranslator(config.messages)
    this.money = new Intl.NumberFormat(`${config.locale}-${config.preset.phone_region}`, {
      style: 'currency',
      currency: config.currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
    const fields = config.preset.steps.flatMap((step) =>
      step.fields.flatMap((field): FieldSpec[] => [field, ...(field.follow_up?.fields ?? [])]),
    )
    this.personal = new Set(fields.filter((field) => field.personal).map((field) => field.id))
    this.slotOrder = fields.flatMap((field) => field.slots.map((slot) => slot.id))
    const id = '(\\d+)'
    this.routes = [
      ['GET', /^\/api\/config$/, () => ({ status: 200, body: this.config })],
      ['POST', /^\/api\/leads$/, (_m, _q, body) => this.createLead(body)],
      ['GET', new RegExp(`^/api/leads/${id}$`), (m) => this.sellerLead(Number(m[1]))],
      ['PATCH', new RegExp(`^/api/leads/${id}$`), (m, _q, body) => this.updateLead(Number(m[1]), body)],
      ['POST', new RegExp(`^/api/leads/${id}/submit$`), (m) => this.submitLead(Number(m[1]))],
      ['DELETE', new RegExp(`^/api/leads/${id}/photos/${id}$`), (m) => this.deletePhoto(Number(m[1]), Number(m[2]))],
      ['GET', /^\/api\/auth\/me$/, () => this.me()],
      ['POST', /^\/api\/auth\/login$/, () => this.signIn(true)],
      ['POST', /^\/api\/auth\/logout$/, () => this.signIn(false)],
      ['POST', /^\/api\/auth\/password$/, () => ({ status: 200, body: { ok: true } })],
      ['GET', /^\/api\/owner\/leads$/, (_m, query) => this.owner(() => this.list(query))],
      ['GET', new RegExp(`^/api/owner/leads/${id}$`), (m) => this.owner(() => this.detail(Number(m[1])))],
      [
        'POST',
        new RegExp(`^/api/owner/leads/${id}/status$`),
        (m, _q, body) => this.owner(() => this.setStatus(Number(m[1]), body)),
      ],
      [
        'POST',
        new RegExp(`^/api/owner/leads/${id}/notes$`),
        (m, _q, body) => this.owner(() => this.addNote(Number(m[1]), body)),
      ],
      [
        'DELETE',
        new RegExp(`^/api/owner/leads/${id}/notes/${id}$`),
        (m) => this.owner(() => this.setNoteDeleted(Number(m[1]), Number(m[2]), true)),
      ],
      [
        'POST',
        new RegExp(`^/api/owner/leads/${id}/notes/${id}/restore$`),
        (m) => this.owner(() => this.setNoteDeleted(Number(m[1]), Number(m[2]), false)),
      ],
      ['GET', /^\/api\/owner\/stats$/, (_m, query) => this.owner(() => this.stats(query.get('period') ?? '30'))],
      ['GET', /^\/api\/owner\/push$/, () => this.owner(() => ({ status: 200, body: this.pushStatus() }))],
      ['POST', /^\/api\/owner\/push\/subscriptions$/, () => this.owner(() => this.setPush(true))],
      ['POST', /^\/api\/owner\/push\/unsubscribe$/, () => this.owner(() => this.setPush(false))],
      ['POST', /^\/api\/owner\/push\/test$/, () => this.owner(() => this.testPush())],
    ]
  }

  // Whether a request has a route here at all (a 404 may also mean "no such lead").
  knows(method: string, path: string): boolean {
    return this.routes.some(([verb, pattern]) => verb === method && pattern.test(path))
  }

  handle(method: string, url: string, body: unknown = {}): Reply {
    const parsed = new URL(url, 'https://demo.invalid')
    for (const [verb, pattern, handler] of this.routes) {
      const match = parsed.pathname.match(pattern)
      if (verb === method && match) return handler(match, parsed.searchParams, (body ?? {}) as Record<string, unknown>)
    }
    return { status: 404 }
  }

  // --- the seller's form -----------------------------------------------------------

  private createLead(body: Record<string, unknown>): Reply {
    const id = this.data.nextId++
    const expiresAt = new Date(this.now().getTime() + 7 * 864e5).toISOString()
    // The honeypot gets a convincing answer and nothing is stored, as on the server.
    if (body.honeypot) return { status: 201, body: { id: id + 9000, token: `demo-${id}`, expiresAt } }
    const now = this.now().toISOString()
    const source = typeof body.source === 'string' && body.source ? body.source : 'direct'
    const lead: DemoLead = {
      id,
      status: 'new',
      createdAt: now,
      submittedAt: null,
      statusChangedAt: now,
      closedAt: null,
      source,
      answers: this.normalize((body.answers ?? {}) as Record<string, Value>),
      photos: [],
      notes: [],
      events: [],
    }
    this.data.leads.push(lead)
    this.announce('new_lead', lead)
    return { status: 201, body: { id, token: `demo-${id}`, expiresAt } }
  }

  private sellerLead(id: number): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    const stored: StoredLead = {
      id,
      answers: lead.answers,
      // The form adds "?token=..." to this address; after "#" it cannot spoil a blob: URL.
      photos: this.ordered(lead).map((p) => ({ id: p.id, slot: p.slot, thumbUrl: `${p.thumb}#` })),
      submitted: lead.submittedAt !== null,
    }
    return { status: 200, body: stored }
  }

  private updateLead(id: number, body: Record<string, unknown>): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    if (lead.submittedAt) return { status: 409 }
    lead.answers = this.normalize((body.answers ?? {}) as Record<string, Value>)
    return { status: 200, body: { id } }
  }

  private submitLead(id: number): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    if (!lead.submittedAt) {
      lead.submittedAt = this.now().toISOString()
      if (lead.photos.length) this.announce('photos_added', lead)
    }
    return { status: 200, body: { id } }
  }

  // Photos arrive through XMLHttpRequest (for the progress bar), not fetch,
  // so the browser layer calls this directly. A guided angle holds one photo.
  addPhoto(id: number, slot: string | null, thumb: string, full: string): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    if (lead.submittedAt) return { status: 409 }
    if (slot) lead.photos = lead.photos.filter((photo) => photo.slot !== slot)
    const photo: DemoPhoto = { id: this.data.nextId++, slot, thumb, full }
    lead.photos.push(photo)
    return { status: 201, body: { id: photo.id, slot, thumbUrl: `${thumb}#` } }
  }

  private deletePhoto(id: number, photoId: number): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    if (lead.submittedAt) return { status: 409 }
    lead.photos = lead.photos.filter((photo) => photo.id !== photoId)
    return { status: 204 }
  }

  // --- the owner's dashboard -------------------------------------------------------

  private me(): Reply {
    if (!this.data.signedIn) return { status: 401 }
    return { status: 200, body: { authenticated: true, passwordChangedAt: null } }
  }

  // Any password opens the demo.
  private signIn(on: boolean): Reply {
    this.data.signedIn = on
    return { status: 200, body: { ok: true } }
  }

  private owner(run: () => Reply): Reply {
    return this.data.signedIn ? run() : { status: 401 }
  }

  private list(query: URLSearchParams): Reply {
    const tab = (query.get('tab') ?? 'new') as Tab
    const statuses = TABS[tab]
    if (statuses === undefined) return { status: 422 }
    const words = (query.get('q') ?? '').split(/\s+/).filter(Boolean)
    const offset = Math.max(0, Number(query.get('offset') ?? 0) || 0)
    const found = this.newestFirst()
      .filter((lead) => !statuses || statuses.includes(lead.status))
      .filter((lead) => words.every((word) => this.matches(lead, word)))
    const counts = { new: 0, in_work: 0, all: this.data.leads.length }
    for (const lead of this.data.leads) {
      if (lead.status === 'new') counts.new++
      if (lead.status === 'in_work') counts.in_work++
    }
    const page = found.slice(offset, offset + PAGE_SIZE)
    const result: LeadList = {
      counts,
      leads: page.map((lead) => this.card(lead)),
      hasMore: found.length > offset + PAGE_SIZE,
    }
    return { status: 200, body: result }
  }

  // Every word must match the car, the seller's details or the lead id;
  // phone numbers match however they are typed (415-555, (415) 555).
  private matches(lead: DemoLead, raw: string): boolean {
    const word = raw.replace(/^#+/, '').toLowerCase()
    if (!word) return true
    const a = lead.answers
    const haystack = [a.make, a.model, a.name, a.phone, a.location, a.email, a.vin, lead.id]
      .filter((value) => value !== undefined && value !== null)
      .join(' ')
      .toLowerCase()
    if (haystack.includes(word)) return true
    const digits = word.replace(/\D/g, '')
    return /^[\d()+.-]+$/.test(word) && digits.length >= 3 && String(a.phone ?? '').replace(/\D/g, '').includes(digits)
  }

  private detail(id: number): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    const result: Detail = {
      ...this.card(lead),
      answers: lead.answers,
      photos: this.ordered(lead).map((p) => this.photo(p)),
      submittedAt: lead.submittedAt,
      closedAt: lead.closedAt,
      statusChangedAt: lead.statusChangedAt,
      purgedAt: null,
      hasPhotos: lead.photos.length > 0,
      notes: lead.notes
        .filter((note) => !note.deleted)
        .sort((x, y) => y.createdAt.localeCompare(x.createdAt) || y.id - x.id)
        .map(({ id, text, createdAt }) => ({ id, text, createdAt })),
      events: [...lead.events].sort((x, y) => y.createdAt.localeCompare(x.createdAt) || y.id - x.id),
    }
    return { status: 200, body: result }
  }

  private setStatus(id: number, body: Record<string, unknown>): Reply {
    const lead = this.find(id)
    const status = body.status as Status
    if (!STATUSES.includes(status)) return { status: 422 }
    if (!lead) return { status: 404 }
    const now = this.now().toISOString()
    if (typeof body.undo === 'number') {
      // Only the latest change can be taken back, as on the server.
      const latest = [...lead.events].sort((x, y) => y.createdAt.localeCompare(x.createdAt) || y.id - x.id)[0]
      if (!latest || latest.id !== body.undo || latest.to !== lead.status || !latest.from) return { status: 409 }
      this.apply(lead, latest.from, now)
      lead.events = lead.events.filter((event) => event.id !== latest.id)
      return { status: 200, body: { status: lead.status, event: null } }
    }
    if (lead.status === status) return { status: 200, body: { status, event: null } }
    const event: LeadEvent = { id: this.data.nextId++, kind: 'status', from: lead.status, to: status, createdAt: now }
    this.apply(lead, status, now)
    lead.events.push(event)
    return { status: 200, body: { status, event } }
  }

  private apply(lead: DemoLead, status: Status, now: string) {
    lead.status = status
    lead.statusChangedAt = now
    lead.closedAt = CLOSED.includes(status) ? now : null
  }

  private addNote(id: number, body: Record<string, unknown>): Reply {
    const lead = this.find(id)
    if (!lead) return { status: 404 }
    const text = String(body.text ?? '').trim()
    if (!text || text.length > NOTE_MAX_LENGTH) return { status: 422 }
    const note: DemoNote = { id: this.data.nextId++, text, createdAt: this.now().toISOString(), deleted: false }
    lead.notes.push(note)
    return { status: 201, body: { id: note.id, text: note.text, createdAt: note.createdAt } }
  }

  private setNoteDeleted(id: number, noteId: number, deleted: boolean): Reply {
    const note = this.find(id)?.notes.find((n) => n.id === noteId)
    if (!note) return { status: 404 }
    note.deleted = deleted
    return deleted ? { status: 204 } : { status: 200, body: { id: note.id, text: note.text, createdAt: note.createdAt } }
  }

  private stats(period: string): Reply {
    if (period !== '7' && period !== '30' && period !== 'all') return { status: 422 }
    const rows = this.data.leads.map((lead) => ({ createdAt: lead.createdAt, status: lead.status, source: lead.source }))
    const result = computeStats(rows, period, this.now(), this.config.timezone)
    for (const source of result.sources) source.label = this.sourceLabel(source.source)
    return { status: 200, body: result }
  }

  private pushStatus(): PushStatus {
    return {
      configured: true,
      publicKey: 'demo',
      devices: this.data.pushOn ? 1 : 0,
      workingDevices: this.data.pushOn ? 1 : 0,
      lastSuccessAt: this.data.pushOn ? this.now().toISOString() : null,
      problem: false,
    }
  }

  private setPush(on: boolean): Reply {
    this.data.pushOn = on
    return { status: 200, body: { ok: true } }
  }

  private testPush(): Reply {
    this.notify({
      title: this.t('notifications.test.title', { brand: this.config.brand.name }),
      body: this.t('notifications.test.body'),
      path: '/app/settings',
    })
    return { status: 200, body: { delivered: 1, failed: 0 } }
  }

  // --- shared -------------------------------------------------------------------------

  private find(id: number): DemoLead | undefined {
    return this.data.leads.find((lead) => lead.id === id)
  }

  private newestFirst(): DemoLead[] {
    return [...this.data.leads].sort((x, y) => y.createdAt.localeCompare(x.createdAt) || y.id - x.id)
  }

  // Guided angles in the preset's order, then the extra photos as they came.
  private ordered(lead: DemoLead): DemoPhoto[] {
    const rank = (photo: DemoPhoto) => {
      const index = photo.slot ? this.slotOrder.indexOf(photo.slot) : -1
      return index >= 0 ? index : this.slotOrder.length
    }
    return [...lead.photos].sort((x, y) => rank(x) - rank(y) || x.id - y.id)
  }

  private photo(photo: DemoPhoto): Photo {
    return { id: photo.id, slot: photo.slot, thumbUrl: photo.thumb, url: photo.full }
  }

  private card(lead: DemoLead): Card {
    const shown = this.ordered(lead)
    const answers = Object.fromEntries(Object.entries(lead.answers).filter(([key]) => !this.personal.has(key)))
    return {
      id: lead.id,
      status: lead.status,
      createdAt: lead.createdAt,
      source: lead.source,
      sourceLabel: this.sourceLabel(lead.source),
      answers,
      photoCount: shown.length,
      photos: shown.slice(0, 1).map((p) => this.photo(p)),
    }
  }

  private sourceLabel(source: string): string {
    if (source in SOURCE_LABELS) return SOURCE_LABELS[source]
    const label = this.t(`sources.${source}`)
    return label === `sources.${source}` ? this.t('sources.other') : label
  }

  // The notification the server builds: the car and the price, never the seller.
  private announce(kind: 'new_lead' | 'photos_added', lead: DemoLead) {
    const { year, make, model, asking_price: price } = lead.answers
    const car =
      typeof year === 'number'
        ? this.t('notifications.car', { year, make: String(make ?? ''), model: String(model ?? '') })
        : this.t('notifications.car_no_year', { make: String(make ?? ''), model: String(model ?? '') }).trim()
    const count = lead.photos.length
    const photos =
      count === 0
        ? this.t('notifications.no_photos')
        : count === 1
          ? this.t('notifications.photos_one')
          : this.t('notifications.photos_other', { count })
    this.notify({
      title: this.t(`notifications.${kind}.title`, { car }),
      body: this.t(`notifications.${kind}.body`, {
        price: typeof price === 'number' ? this.money.format(price) : this.t('notifications.no_price'),
        photos,
      }),
      path: `/app/leads/${lead.id}`,
    })
  }
}

// --- statistics, as app/services/stats.py computes them -----------------------------

interface StatsRow {
  createdAt: string
  status: Status
  source: string
}

// YYYY-MM-DD of an instant in the owner's time zone.
function dayIn(date: Date, timeZone: string): string {
  return new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone }).format(date)
}

function addDays(day: string, days: number): string {
  const [y, m, d] = day.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10)
}

// Monday is 0, as Python's weekday().
function weekday(day: string): number {
  return (new Date(`${day}T12:00:00Z`).getUTCDay() + 6) % 7
}

// The instant a day starts in the owner's time zone.
export function midnight(day: string, timeZone: string): Date {
  const [y, m, d] = day.split('-').map(Number)
  const guess = Date.UTC(y, m - 1, d)
  const offset = (at: number) => {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      second: 'numeric',
    }).formatToParts(new Date(at))
    const part = (type: string) => Number(parts.find((p) => p.type === type)?.value)
    const wall = Date.UTC(part('year'), part('month') - 1, part('day'), part('hour'), part('minute'), part('second'))
    return wall - at
  }
  const first = guess - offset(guess)
  return new Date(guess - offset(first))
}

export function computeStats(rows: StatsRow[], period: Stats['period'], now: Date, timeZone: string): Stats {
  const today = dayIn(now, timeZone)
  const start = period === 'all' ? null : midnight(addDays(today, -(Number(period) - 1)), timeZone)
  const weekStartDay = addDays(today, -weekday(today))
  const weekStart = midnight(weekStartDay, timeZone)
  const at = (row: StatsRow) => new Date(row.createdAt).getTime()
  const inPeriod = rows.filter((row) => !start || at(row) >= start.getTime())
  const received = new Map<string, number>()
  const purchased = new Map<string, number>()
  for (const row of inPeriod) {
    received.set(row.source, (received.get(row.source) ?? 0) + 1)
    if (row.status === 'bought') purchased.set(row.source, (purchased.get(row.source) ?? 0) + 1)
  }
  const sources = [...received.entries()]
    .sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
    .map(([source, leads]) => ({ source, label: source, leads, purchased: purchased.get(source) ?? 0 }))

  let edges: [string, Date, Date][] = []
  if (period === '7') {
    for (let back = 6; back >= 0; back--) {
      const day = addDays(today, -back)
      edges.push([day, midnight(day, timeZone), midnight(addDays(day, 1), timeZone)])
    }
  } else if (inPeriod.length || start) {
    const first = inPeriod.length ? new Date(Math.min(...inPeriod.map(at))) : start!
    const begin = start && start > first ? start : first
    let monday = dayIn(begin, timeZone)
    monday = addDays(monday, -weekday(monday))
    edges = []
    while (monday <= weekStartDay) {
      edges.push([monday, midnight(monday, timeZone), midnight(addDays(monday, 7), timeZone)])
      monday = addDays(monday, 7)
    }
  }
  const buckets = edges.map(([day, low, high]) => {
    const inside = inPeriod.filter((row) => at(row) >= low.getTime() && at(row) < high.getTime())
    return { start: day, leads: inside.length, purchased: inside.filter((row) => row.status === 'bought').length }
  })
  const firstLead = rows.length ? new Date(Math.min(...rows.map(at))) : null
  return {
    period,
    total: inPeriod.length,
    week: rows.filter((row) => at(row) >= weekStart.getTime()).length,
    weekStart: weekStartDay,
    purchased: inPeriod.filter((row) => row.status === 'bought').length,
    firstLeadAt: firstLead ? firstLead.toISOString() : null,
    sources,
    buckets,
  }
}
