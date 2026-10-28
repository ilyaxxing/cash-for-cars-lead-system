// The leads a visitor finds in the demo dashboard. All fictional: 555-01xx
// phone numbers, example.com addresses, AI-generated car photos with the
// makers' badges painted out. Times count back from the moment the page
// opens, so the newest lead always arrived today.

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

const HOUR = 36e5

interface Featured {
  hoursAgo: number
  status: Status
  source: string
  answers: Record<string, Value>
  photos: [string | null, string, string][]
  notes?: [number, string][]
}

// Leads with photos, newest first: the ones a visitor opens.
const FEATURED: Featured[] = [
  {
    hoursAgo: 0.6,
    status: 'new',
    source: 'card',
    answers: {
      make: 'Kia', model: 'Optima', year: 2017, mileage: 78400, condition: 'good', accident: 'no',
      finance: 'no', asking_price: 9800, location: 'Austin', postal_code: '78704', vin: '5XXGT4L32HG123456',
      name: 'Jordan Reyes', phone: '+15125550142', contact_method: 'call',
    },
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
    answers: {
      make: 'Hyundai', model: 'Kona', year: 2019, mileage: 46200, condition: 'excellent', accident: 'no',
      finance: 'yes', finance_details: 'About $6,000 left on the loan.', asking_price: 14200,
      location: 'Round Rock', postal_code: '78664', name: 'Avery Brooks', phone: '+15125550117',
      email: 'avery@example.com', contact_method: 'sms',
    },
    photos: [['rear_right', suvThumb, suv]],
  },
  {
    hoursAgo: 26,
    status: 'new',
    source: 'card',
    answers: {
      make: 'Hyundai', model: 'Accent', year: 2014, mileage: 131000, condition: 'accident_damaged',
      accident: 'yes', accident_details: 'Front-end collision last spring. It still drives.', finance: 'no',
      asking_price: 2900, location: 'Pflugerville', postal_code: '78660', name: 'Casey Hayes',
      phone: '+15125550163', contact_method: 'whatsapp',
    },
    photos: [['front_left', hatchbackThumb, hatchback]],
  },
  {
    hoursAgo: 50,
    status: 'in_work',
    source: 'card',
    answers: {
      make: 'Ford', model: 'F-150', year: 2016, mileage: 121500, condition: 'good', accident: 'no',
      finance: 'no', asking_price: 18500, location: 'Cedar Park', postal_code: '78613',
      vin: '1FTEW1EF5GFA12345', name: 'Morgan Price', phone: '+15125550128', contact_method: 'call',
    },
    photos: [['front_left', truckThumb, truck]],
    notes: [[30, 'Called the seller, viewing booked for Thursday.']],
  },
  {
    hoursAgo: 74,
    status: 'in_work',
    source: 'flyer',
    answers: {
      make: 'Honda', model: 'Odyssey', year: 2017, mileage: 88000, condition: 'good', accident: 'unknown',
      finance: 'no', asking_price: 16900, location: 'Austin', postal_code: '78745', name: 'Taylor Ellis',
      phone: '+15125550189', email: 'taylor@example.com', contact_method: 'email',
    },
    photos: [['front_left', minivanThumb, minivan]],
    notes: [[52, 'Offered 1,500 under asking; seller is thinking it over.']],
  },
  {
    hoursAgo: 150,
    status: 'bought',
    source: 'card',
    answers: {
      make: 'Hyundai', model: 'Genesis', year: 2013, mileage: 162000, condition: 'not_running', accident: 'no',
      finance: 'no', location: 'Austin', postal_code: '78723', name: 'Riley Grant', phone: '+15125550104',
      contact_method: 'call',
    },
    photos: [['front_right', blackSedanThumb, blackSedan]],
    notes: [[120, 'Towed on Saturday, paid in cash.']],
  },
]

// Older leads without photos, so the lists and statistics look lived in.
const CARS: [string, string][] = [
  ['Toyota', 'Camry'], ['Toyota', 'RAV4'], ['Ford', 'Escape'], ['Chevrolet', 'Silverado'], ['Honda', 'Civic'],
  ['Honda', 'CR-V'], ['Nissan', 'Altima'], ['Jeep', 'Wrangler'], ['Kia', 'Sorento'], ['Subaru', 'Outback'],
  ['Ram', '1500'], ['Mazda', 'CX-5'], ['Chevrolet', 'Malibu'], ['Toyota', 'Corolla'],
]
const FIRST = ['Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Avery', 'Quinn', 'Jamie', 'Drew', 'Sam']
const LAST = ['Lee', 'Parker', 'Reed', 'Brooks', 'Hayes', 'Price', 'Ellis', 'Grant', 'Shaw', 'Cole']
const CITIES: [string, string][] = [['Austin', '78701'], ['Round Rock', '78681'], ['San Marcos', '78666'], ['Georgetown', '78626']]
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

export function seed(now: Date): DemoData {
  const data: DemoData = { leads: [], nextId: 1000, signedIn: true, pushOn: true }
  const at = (hoursAgo: number) => new Date(now.getTime() - hoursAgo * HOUR).toISOString()
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
    const [make, model] = pick(CARS)
    const [location, postal] = pick(CITIES)
    const hasPrice = random() < 0.75
    add(
      {
        status: hoursAgo < 140 ? 'new' : hoursAgo < 260 ? 'in_work' : pick(OUTCOMES),
        createdAt: at(hoursAgo),
        submittedAt: at(hoursAgo - 0.05),
        source: pick(SOURCES),
        answers: {
          make, model,
          year: 2006 + Math.floor(random() * 19),
          mileage: (20 + Math.floor(random() * 170)) * 1000,
          condition: pick(CONDITIONS),
          accident: pick(['no', 'no', 'yes', 'unknown']),
          finance: pick(['no', 'no', 'yes']),
          ...(hasPrice ? { asking_price: (25 + Math.floor(random() * 300)) * 100 } : {}),
          location, postal_code: postal,
          name: `${pick(FIRST)} ${pick(LAST)}`,
          phone: `+1512555${String(100 + Math.floor(random() * 100)).padStart(4, '0')}`,
          contact_method: pick(['call', 'call', 'sms', 'whatsapp']),
        },
        photos: [],
        notes: [],
      },
      hoursAgo - 20,
    )
  }

  for (const lead of [...FEATURED].reverse()) {
    const photos: DemoPhoto[] = lead.photos.map(([slot, thumb, full]) => ({ id: data.nextId++, slot, thumb, full }))
    add(
      {
        status: lead.status,
        createdAt: at(lead.hoursAgo),
        submittedAt: at(lead.hoursAgo - 0.05),
        source: lead.source,
        answers: lead.answers,
        photos,
        notes: (lead.notes ?? []).map(([hoursAgo, text]) => ({ id: data.nextId++, text, createdAt: at(hoursAgo), deleted: false })),
      },
      lead.hoursAgo - 2,
    )
  }
  return data
}
