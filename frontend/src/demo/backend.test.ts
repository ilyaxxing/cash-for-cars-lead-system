import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { parse } from 'yaml'
import type { Card, Detail, LeadList, Stats } from '../dashboard/api'
import type { AppConfig, Preset } from '../shared/config'
import { normalizeUsPhone } from '../shared/region'
import { Backend, computeStats, midnight, type DemoData, type Notice } from './backend'
import { seed } from './seed'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')

// The shipped preset, with the defaults the server adds when it serializes it.
function loadPreset(): Preset {
  const raw = parse(read('../../../presets/us-car-buyout.yaml'))
  for (const step of raw.steps) {
    Object.assign(step, { enabled: true, skippable: false, submit: false, consent: false, show_chips: false, ...step })
    for (const field of step.fields.flatMap((f: any) => [f, ...(f.follow_up?.fields ?? [])])) {
      Object.assign(field, {
        required: false, personal: false, options: [], unknown: false, multiline: false,
        suggestions: [], other: false, chip: false, slots: [], extra: 0, ...field,
      })
    }
  }
  return raw as Preset
}

const config: AppConfig = {
  brand: { name: 'Car Buyout', phone: '', logo: null, photo: null },
  operator: 'Example Auto LLC',
  locale: 'en',
  currency: 'USD',
  timezone: 'America/Chicago',
  preset: loadPreset(),
  messages: JSON.parse(read('../../../locales/en.json')),
  privacyUrl: '/privacy',
  retentionDays: 90,
}

const NOW = new Date('2026-10-21T17:00:00Z') // a Wednesday, noon in Austin

function setup(data: DemoData = { leads: [], nextId: 1, signedIn: true, pushOn: true }) {
  const notices: Notice[] = []
  const normalize = (answers: Record<string, unknown>) =>
    typeof answers.phone === 'string' ? { ...answers, phone: normalizeUsPhone(answers.phone) ?? answers.phone } : answers
  const backend = new Backend(data, config, (n) => notices.push(n), normalize as never, () => NOW)
  const call = (method: string, url: string, body?: unknown) => backend.handle(method, url, body)
  return { backend, call, notices, data }
}

const ANSWERS = {
  make: 'Toyota', model: 'Camry', year: 2019, mileage: 64000, condition: 'good', accident: 'no', finance: 'no',
  asking_price: 12500, location: 'Austin', postal_code: '78702', name: 'Sam Demo', phone: '512-555-0199',
  contact_method: 'call',
}

describe('the demo answers every request the apps make', () => {
  // Every API address in the form and the dashboard, with ids filled in.
  // Photo uploads go through XMLHttpRequest, which browser.ts hands to addPhoto.
  const calls = [read('../form/api.ts'), read('../dashboard/api.ts')]
    .flatMap((source) =>
      [...source.matchAll(/'(GET|POST|PATCH|DELETE)',\s*[`'](\/api\/[^`'?]*)/g)].map(([, method, path]) => [
        method,
        path.replace(/\$\{[^}]+\}/g, '7'),
      ]),
    )
    .filter(([method, path]) => !(method === 'POST' && path.endsWith('/photos')))

  it('finds the calls', () => expect(calls.length).toBeGreaterThanOrEqual(20))

  it.each(calls)('%s %s', (method, path) => {
    expect(setup().backend.knows(method, path)).toBe(true)
  })
})

describe('a seller sends an inquiry', () => {
  it('lands in the dashboard with the notifications the server would send', () => {
    const { backend, call, notices } = setup()
    const created = call('POST', '/api/leads', { answers: ANSWERS, source: 'card', honeypot: '' })
    expect(created.status).toBe(201)
    const { id } = created.body as { id: number }
    expect(notices[0]).toEqual({
      title: 'New lead: 2019 Toyota Camry',
      body: '$12,500 · No photos yet',
      path: `/app/leads/${id}`,
    })

    const list = call('GET', '/api/owner/leads?tab=new').body as LeadList
    expect(list.counts).toEqual({ new: 1, in_work: 0, all: 1 })
    const card: Card = list.leads[0]
    expect(card.sourceLabel).toBe('Business Card')
    // List cards never carry personal fields.
    expect(card.answers).not.toHaveProperty('name')
    expect(card.answers).not.toHaveProperty('phone')

    backend.addPhoto(id, 'rear_right', 'blob:a', 'blob:a')
    backend.addPhoto(id, 'front_left', 'blob:b', 'blob:b')
    backend.addPhoto(id, 'front_left', 'blob:c', 'blob:c') // a guided angle holds one photo
    const stored = call('GET', `/api/leads/${id}`).body as { photos: { slot: string; thumbUrl: string }[] }
    expect(stored.photos.map((p) => [p.slot, p.thumbUrl])).toEqual([['front_left', 'blob:c#'], ['rear_right', 'blob:a#']])

    expect(call('POST', `/api/leads/${id}/submit`).status).toBe(200)
    expect(notices[1].title).toBe('Photos added: 2019 Toyota Camry')
    expect(notices[1].body).toBe('2 photos · $12,500')
    expect(call('PATCH', `/api/leads/${id}`, { answers: ANSWERS }).status).toBe(409)

    const detail = call('GET', `/api/owner/leads/${id}`).body as Detail
    expect(detail.answers.phone).toBe('+15125550199')
    expect(detail.photoCount).toBe(2)
    expect(detail.submittedAt).toBe(NOW.toISOString())
  })

  it('keeps nothing from a bot that filled in the honeypot', () => {
    const { call, notices, data } = setup()
    expect(call('POST', '/api/leads', { answers: ANSWERS, honeypot: 'x' }).status).toBe(201)
    expect(data.leads).toHaveLength(0)
    expect(notices).toHaveLength(0)
  })
})

describe('the owner works a lead', () => {
  const created = () => {
    const env = setup()
    const { id } = env.call('POST', '/api/leads', { answers: ANSWERS }).body as { id: number }
    return { ...env, id }
  }

  it('changes the status, and can take the latest change back', () => {
    const { call, id } = created()
    const moved = call('POST', `/api/owner/leads/${id}/status`, { status: 'in_work' }).body as { event: { id: number } }
    expect(moved.event).toMatchObject({ kind: 'status', from: 'new', to: 'in_work' })
    expect((call('GET', '/api/owner/leads?tab=in_work').body as LeadList).leads).toHaveLength(1)

    expect(call('POST', `/api/owner/leads/${id}/status`, { status: 'in_work', undo: moved.event.id }).status).toBe(200)
    const detail = call('GET', `/api/owner/leads/${id}`).body as Detail
    expect(detail.status).toBe('new')
    expect(detail.events).toHaveLength(0)
    expect(call('POST', `/api/owner/leads/${id}/status`, { status: 'new', undo: moved.event.id }).status).toBe(409)
  })

  it('sets closedAt on entering a closed status and clears it on leaving', () => {
    const { call, id } = created()
    call('POST', `/api/owner/leads/${id}/status`, { status: 'bought' })
    expect((call('GET', `/api/owner/leads/${id}`).body as Detail).closedAt).toBe(NOW.toISOString())
    call('POST', `/api/owner/leads/${id}/status`, { status: 'in_work' })
    expect((call('GET', `/api/owner/leads/${id}`).body as Detail).closedAt).toBeNull()
  })

  it('adds, deletes and restores notes', () => {
    const { call, id } = created()
    expect(call('POST', `/api/owner/leads/${id}/notes`, { text: '   ' }).status).toBe(422)
    const note = call('POST', `/api/owner/leads/${id}/notes`, { text: ' Viewing on Thursday ' }).body as { id: number; text: string }
    expect(note.text).toBe('Viewing on Thursday')
    call('DELETE', `/api/owner/leads/${id}/notes/${note.id}`)
    expect((call('GET', `/api/owner/leads/${id}`).body as Detail).notes).toHaveLength(0)
    call('POST', `/api/owner/leads/${id}/notes/${note.id}/restore`)
    expect((call('GET', `/api/owner/leads/${id}`).body as Detail).notes).toHaveLength(1)
  })

  it('finds a lead by its car, its id or the phone however it is typed', () => {
    const { call, id } = created()
    const found = (q: string) => (call('GET', `/api/owner/leads?tab=all&q=${encodeURIComponent(q)}`).body as LeadList).leads.length
    expect(found('camry')).toBe(1)
    expect(found(`#${id}`)).toBe(1)
    expect(found('(512) 555-0199')).toBe(1)
    expect(found('toyota corolla')).toBe(0)
  })

  it('asks a signed-out visitor to sign in, and any password opens it', () => {
    const { call } = setup()
    call('POST', '/api/auth/logout')
    expect(call('GET', '/api/owner/leads').status).toBe(401)
    expect(call('GET', '/api/auth/me').status).toBe(401)
    call('POST', '/api/auth/login', { password: 'anything' })
    expect(call('GET', '/api/owner/leads').status).toBe(200)
  })
})

describe('statistics, as the server computes them', () => {
  it('starts days at midnight in the owner time zone, across daylight saving', () => {
    expect(midnight('2026-10-21', 'America/Chicago').toISOString()).toBe('2026-10-21T05:00:00.000Z')
    expect(midnight('2026-11-02', 'America/Chicago').toISOString()).toBe('2026-11-02T06:00:00.000Z')
    expect(midnight('2026-03-08', 'America/Chicago').toISOString()).toBe('2026-03-08T06:00:00.000Z')
  })

  it('counts the period, this week from Monday and the sources', () => {
    const rows = [
      { createdAt: '2026-10-21T16:00:00Z', status: 'new' as const, source: 'card' },
      { createdAt: '2026-10-19T15:00:00Z', status: 'in_work' as const, source: 'card' },
      // Sunday evening in Austin: last week, though Monday already in UTC.
      { createdAt: '2026-10-19T03:00:00Z', status: 'rejected' as const, source: 'parking' },
      { createdAt: '2026-10-01T15:00:00Z', status: 'bought' as const, source: 'card' },
      { createdAt: '2026-08-01T15:00:00Z', status: 'bought' as const, source: 'flyer' },
    ]
    const month: Stats = computeStats(rows, '30', NOW, 'America/Chicago')
    expect(month).toMatchObject({ total: 4, week: 2, weekStart: '2026-10-19', purchased: 1 })
    expect(month.sources.map((s) => [s.source, s.leads, s.purchased])).toEqual([['card', 3, 1], ['parking', 1, 0]])
    expect(month.buckets.map((b) => b.start)).toEqual(['2026-09-28', '2026-10-05', '2026-10-12', '2026-10-19'])
    expect(month.firstLeadAt).toBe('2026-08-01T15:00:00.000Z')

    const week = computeStats(rows, '7', NOW, 'America/Chicago')
    expect(week.buckets).toHaveLength(7)
    expect(week.buckets.at(-1)).toEqual({ start: '2026-10-21', leads: 1, purchased: 0 })
    expect(computeStats(rows, 'all', NOW, 'America/Chicago').total).toBe(5)
  })
})

describe('the demo leads', () => {
  it('are the same on every visit, fictional, and include today', () => {
    const first = seed(NOW)
    expect(seed(NOW)).toEqual(first)
    for (const lead of first.leads) {
      expect(String(lead.answers.phone)).toMatch(/^\+151255501\d\d$/)
      expect(lead.answers.make).toBeTruthy()
    }
    const today = first.leads.filter((lead) => NOW.getTime() - new Date(lead.createdAt).getTime() < 864e5)
    expect(today.length).toBeGreaterThan(0)
    expect(first.leads.filter((lead) => lead.photos.length).length).toBe(6)
  })
})
