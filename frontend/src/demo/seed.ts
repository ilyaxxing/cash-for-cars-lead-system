// The leads a visitor finds in the demo dashboard. The shape of each one (its
// car photos, status, age and condition) is here; everything that depends on
// the country (names, cities, phones, prices, notes) comes from
// countries/<code>/demo.yaml, which tools/make_demo.py puts into the page.
// All fictional: made-up people, example.com addresses, AI-generated car
// photos with the makers' badges painted out. Times count back from the
// moment the page opens, so the newest lead always arrived today.

import type { LeadEvent, Status } from '../dashboard/api'
import type { Value } from '../form/engine'
import type { DemoData, DemoLead, DemoPhoto } from './backend'
import blackSedan from './photos/black-sedan.webp'
import blackSedanThumb from './photos/black-sedan-thumb.webp'
import hatchback from './photos/hatchback.webp'
import hatchbackThumb from './photos/hatchback-thumb.webp'
import minivan from './photos/minivan.webp'
import minivanThumb from './photos/minivan-thumb.webp'
import sedanCluster from './photos/sedan-cluster.webp'
import sedanClusterThumb from './photos/sedan-cluster-thumb.webp'
import sedanFront from './photos/sedan-front.webp'
import sedanFrontThumb from './photos/sedan-front-thumb.webp'
import sedanInterior from './photos/sedan-interior.webp'
import sedanInteriorThumb from './photos/sedan-interior-thumb.webp'
import sedanRear from './photos/sedan-rear.webp'
import sedanRearThumb from './photos/sedan-rear-thumb.webp'
import suv from './photos/suv.webp'
import suvThumb from './photos/suv-thumb.webp'
import truck from './photos/truck.webp'
import truckThumb from './photos/truck-thumb.webp'

// A country's part of the demo, as tools/make_demo.py writes it into the page.
export interface DemoCountry {
  // Names of the made-up business, replaced by a named link's (browser.ts).
  business_names: string[]
  sources: Record<string, string>
  calls_off: string
  price_scale: number
  price_step: number
  distance_unit: 'mi' | 'km'
  // One per lead in FEATURED, in that order: what the seller wrote (the
  // country's own fields too), and a note.
  featured: Record<string, Value>[]
  // The country's own fields for the older leads: one value picked from each list.
  extra: Record<string, Value[]>
  phones: string[]
  cars: [string, string][]
  names: string[]
  cities: [string, string][]
}

const HOUR = 36e5
const KM_PER_MILE = 1.609

interface Featured {
  hoursAgo: number
  status: Status
  source: string
  answers: Record<string, Value>
  photos: [string | null, string, string][]
  noteHoursAgo?: number
}

// Leads with photos, newest first: the ones a visitor opens. Prices in US
// dollars and mileage in miles; the country converts them.
const FEATURED: Featured[] = [
  {
    hoursAgo: 0.6,
    status: 'new',
    source: 'card',
    answers: { year: 2017, mileage: 78400, condition: 'good', accident: 'no', finance: 'no', asking_price: 9800, contact_method: 'call' },
    photos: [
      ['front_left', sedanFrontThumb, sedanFront],
      ['rear_right', sedanRearThumb, sedanRear],
      ['interior', sedanInteriorThumb, sedanInterior],
      ['cluster', sedanClusterThumb, sedanCluster],
    ],
  },
  {
    hoursAgo: 5,
    status: 'new',
    source: 'parking',
    answers: { year: 2019, mileage: 46200, condition: 'excellent', accident: 'no', finance: 'yes', asking_price: 14200, contact_method: 'sms' },
    photos: [['rear_right', suvThumb, suv]],
  },
  {
    hoursAgo: 26,
    status: 'new',
    source: 'card',
    answers: { year: 2014, mileage: 131000, condition: 'accident_damaged', accident: 'yes', finance: 'no', asking_price: 2900, contact_method: 'whatsapp' },
    photos: [['front_left', hatchbackThumb, hatchback]],
  },
  {
    hoursAgo: 50,
    status: 'in_work',
    source: 'card',
    answers: { year: 2016, mileage: 121500, condition: 'good', accident: 'no', finance: 'no', asking_price: 18500, contact_method: 'call' },
    photos: [['front_left', truckThumb, truck]],
    noteHoursAgo: 30,
  },
  {
    hoursAgo: 74,
    status: 'in_work',
    source: 'flyer',
    answers: { year: 2017, mileage: 88000, condition: 'good', accident: 'unknown', finance: 'no', asking_price: 16900, contact_method: 'email' },
    photos: [['front_left', minivanThumb, minivan]],
    noteHoursAgo: 52,
  },
  {
    hoursAgo: 150,
    status: 'bought',
    source: 'card',
    answers: { year: 2013, mileage: 162000, condition: 'not_running', accident: 'no', finance: 'no', contact_method: 'call' },
    photos: [['front_right', blackSedanThumb, blackSedan]],
    noteHoursAgo: 120,
  },
]

const CONDITIONS = ['excellent', 'good', 'good', 'needs_repairs', 'accident_damaged', 'not_running']
const SOURCES = ['card', 'card', 'card', 'card', 'parking', 'flyer', 'direct']
// Older leads mostly reached an outcome; the recent ones are still open.
const OUTCOMES: Status[] = ['bought', 'rejected', 'rejected', 'bought', 'rejected', 'in_work']

// A small fixed sequence: the same demo on every visit.
function sequence(seed: number) {
  let state = seed
  return () => {
    state = (state * 1103515245 + 12345) % 2147483648
    return state / 2147483648
  }
}

export function seed(now: Date, country: DemoCountry): DemoData {
  const data: DemoData = { leads: [], nextId: 1000, signedIn: true, pushOn: true }
  const at = (hoursAgo: number) => new Date(now.getTime() - hoursAgo * HOUR).toISOString()
  const price = (dollars: number) =>
    Math.max(country.price_step, Math.round((dollars * country.price_scale) / country.price_step) * country.price_step)
  const distance = (miles: number) =>
    country.distance_unit === 'km' ? Math.round((miles * KM_PER_MILE) / 100) * 100 : miles
  const local = (answers: Record<string, Value>) => {
    const result = { ...answers }
    if (typeof result.asking_price === 'number') result.asking_price = price(result.asking_price)
    if (typeof result.mileage === 'number') result.mileage = distance(result.mileage)
    return result
  }
  const add = (lead: Omit<DemoLead, 'id' | 'events' | 'statusChangedAt' | 'closedAt'>, changedHoursAgo: number) => {
    const id = data.nextId++
    const events: LeadEvent[] = []
    const changed = lead.status === 'new' ? lead.createdAt : at(changedHoursAgo)
    if (lead.status !== 'new') {
      events.push({ id: data.nextId++, kind: 'status', from: 'new', to: lead.status, createdAt: changed })
    }
    data.leads.push({
      ...lead,
      id,
      events,
      statusChangedAt: changed,
      closedAt: lead.status === 'bought' || lead.status === 'rejected' ? changed : null,
    })
  }

  const random = sequence(7)
  const pick = <T,>(items: T[]) => items[Math.floor(random() * items.length)]
  for (let index = 40; index >= 0; index--) {
    const hoursAgo = 96 + index * 30 + Math.floor(random() * 12)
    const [make, model] = pick(country.cars)
    const [location, postal] = pick(country.cities)
    const hasPrice = random() < 0.75
    add(
      {
        status: hoursAgo < 140 ? 'new' : hoursAgo < 260 ? 'in_work' : pick(OUTCOMES),
        createdAt: at(hoursAgo),
        submittedAt: at(hoursAgo - 0.05),
        source: pick(SOURCES),
        answers: local({
          make, model,
          year: 2006 + Math.floor(random() * 19),
          mileage: (20 + Math.floor(random() * 170)) * 1000,
          condition: pick(CONDITIONS),
          accident: pick(['no', 'no', 'yes', 'unknown']),
          finance: pick(['no', 'no', 'yes']),
          ...(hasPrice ? { asking_price: (25 + Math.floor(random() * 300)) * 100 } : {}),
          location, postal_code: postal,
          name: pick(country.names),
          phone: pick(country.phones),
          contact_method: pick(['call', 'call', 'sms', 'whatsapp']),
          ...Object.fromEntries(Object.entries(country.extra).map(([key, values]) => [key, pick(values)])),
        }),
        photos: [],
        notes: [],
      },
      hoursAgo - 20,
    )
  }

  for (let index = FEATURED.length - 1; index >= 0; index--) {
    const lead = FEATURED[index]
    const { note, ...seller } = country.featured[index] ?? {}
    const photos: DemoPhoto[] = lead.photos.map(([slot, thumb, full]) => ({ id: data.nextId++, slot, thumb, full }))
    const notes = typeof note === 'string' && lead.noteHoursAgo !== undefined
      ? [{ id: data.nextId++, text: note, createdAt: at(lead.noteHoursAgo), deleted: false }]
      : []
    add(
      {
        status: lead.status,
        createdAt: at(lead.hoursAgo),
        submittedAt: at(lead.hoursAgo - 0.05),
        source: lead.source,
        answers: local({ ...lead.answers, ...seller, phone: country.phones[index % country.phones.length] }),
        photos,
        notes,
      },
      lead.hoursAgo - 2,
    )
  }
  return data
}
