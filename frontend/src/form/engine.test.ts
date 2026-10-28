import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { parse } from 'yaml'
import type { Preset } from '../shared/config'
import { isPostalCode, normalizePhone, normalizeUsPhone, prepareRegion } from '../shared/region'
import {
  EARLIER,
  clearStep,
  loadSaved,
  maxDigits,
  payload,
  progress,
  rememberSource,
  screenIds,
  stepById,
  suggestionsFor,
  validateStep,
  vinError,
  yearOptions,
  type Answers,
} from './engine'

// The shipped preset, with the defaults the server adds when it serializes it.
function loadPreset(): Preset {
  const raw = parse(readFileSync(new URL('../../../presets/us-car-buyout.yaml', import.meta.url), 'utf8'))
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

const preset = loadPreset()
const TODAY = new Date(2026, 9, 19)
const step = (id: string) => stepById(preset, id)!

const COMPLETE: Answers = {
  make: 'Toyota', model: 'Camry', year: 2019, mileage: 78400, condition: 'good',
  accident: 'no', finance: 'no', asking_price: 21500, location: 'San Francisco',
  postal_code: '94110', vin: '1HGCM82633A004352', name: 'Jordan Lee',
  phone: '(415) 555-0142', contact_method: 'call',
}

describe('screens and progress', () => {
  it('follows the agreed flow', () => {
    expect(screenIds(preset)).toEqual([
      'welcome', 'vehicle', 'year_mileage', 'condition', 'accident', 'finance',
      'price', 'location', 'vin', 'contact', 'photos', 'review', 'success',
    ])
  })

  it('counts like the design: welcome is 1, review is 12 of 12', () => {
    const ids = screenIds(preset)
    expect(progress(ids, 'year_mileage')).toMatchObject({ n: 3, total: 12, last: false })
    expect(progress(ids, 'review')).toMatchObject({ n: 12, total: 12, last: true })
    expect(progress(ids, 'year_mileage').segments.slice(0, 3)).toEqual([1, 0.45, 0])
  })

  it('renumbers when a step is switched off', () => {
    const withoutLocation = { ...preset, steps: preset.steps.map((s) => (s.id === 'location' ? { ...s, enabled: false } : s)) }
    expect(progress(screenIds(withoutLocation), 'review').total).toBe(11)
  })
})

describe('validation', () => {
  it('accepts a complete contact step', () => {
    expect(validateStep(step('contact'), COMPLETE, TODAY)).toEqual({})
  })

  it('reports codes the locale has text for', () => {
    expect(validateStep(step('contact'), { ...COMPLETE, phone: '12', name: '' }, TODAY)).toEqual({
      name: { code: 'required' },
      phone: { code: 'format' },
    })
  })

  it('requires email only when it is the preferred method', () => {
    expect(validateStep(step('contact'), { ...COMPLETE, contact_method: 'email' }, TODAY)).toEqual({
      email: { code: 'required' },
    })
  })

  it('lets a skippable step be left blank but not half-filled', () => {
    expect(validateStep(step('location'), {}, TODAY)).toEqual({})
    expect(validateStep(step('location'), { location: 'Austin' }, TODAY)).toEqual({
      postal_code: { code: 'required' },
    })
  })

  it('checks the follow-up only when it is unlocked', () => {
    const accident = step('accident')
    expect(validateStep(accident, { accident: 'unknown' }, TODAY)).toEqual({})
    expect(validateStep(accident, {}, TODAY)).toEqual({ accident: { code: 'required' } })
  })

  it('applies the year and mileage limits the server applies', () => {
    const errors = validateStep(step('year_mileage'), { year: 2028, mileage: 990000 }, TODAY)
    expect(errors.year.code).toBe('max')
    expect(errors.mileage.code).toBe('max')
    expect(validateStep(step('year_mileage'), { year: EARLIER, mileage: 5 }, TODAY)).toEqual({})
  })

  it('explains a short VIN with its length', () => {
    expect(vinError('WBA8E5G55KNO1')).toEqual({ code: 'length', params: { count: 13 } })
    expect(vinError('1HGCM82633A0O4352')).toEqual({ code: 'format' })
    expect(vinError('1hgcm82633a004352')).toBeNull()
  })

  it('normalizes US phone numbers like the server', () => {
    expect(normalizeUsPhone('1-415-555-0142')).toBe('+14155550142')
    expect(normalizeUsPhone('(015) 555-0142')).toBeNull()
    expect(normalizePhone('+44 20 7946 0958')).toBeNull() // pii-allow: UK drama range
    expect(isPostalCode('94110-1234')).toBe(true)
    expect(isPostalCode('101000')).toBe(false)
  })

  it("checks another country's numbers and postal codes like the server", async () => {
    await prepareRegion({ phone_region: 'RU', postal_code_pattern: '\\d{6}' })
    try {
      expect(normalizePhone('8 912 345-67-89')).toBe('+79123456789') // pii-allow: fake number
      expect(normalizePhone('+7 912 345 67 89')).toBe('+79123456789') // pii-allow: fake number
      expect(normalizePhone('+1 415 555 0142')).toBeNull() // pii-allow: fake number
      expect(normalizePhone('12345')).toBeNull()
      expect(isPostalCode(' 101000 ')).toBe(true)
      expect(isPostalCode('94110')).toBe(false)
    } finally {
      await prepareRegion({ phone_region: 'US' })
    }
  })
})

describe('answers', () => {
  it('sends numbers as numbers, fills defaults and drops locked follow-ups', () => {
    const body = payload(preset, {
      ...COMPLETE, mileage: '78,400', contact_method: undefined,
      accident: 'no', accident_details: 'left over from an earlier answer',
    })
    expect(body.mileage).toBe(78400)
    expect(body.contact_method).toBe('call')
    expect(body).not.toHaveProperty('accident_details')
  })

  it('forgets a skipped step', () => {
    expect(clearStep(step('location'), { location: 'Austin', postal_code: '78701', vin: 'x' })).toEqual({ vin: 'x' })
  })

  it('suggests models for the chosen make', () => {
    const model = step('vehicle').fields[1]
    expect(suggestionsFor(model, { make: 'Ford' })).toContain('F-150')
    expect(suggestionsFor(model, { make: 'Subaru' })).toEqual([])
  })

  it('offers twelve recent years, older ones on request', () => {
    const { recent, older } = yearOptions(step('year_mileage').fields[0], TODAY)
    expect(recent[0]).toBe(2026)
    expect(recent).toHaveLength(12)
    expect(older.at(-1)).toBe(1990)
  })
})

describe('source and saved progress', () => {
  it('keeps the first meaningful source', () => {
    expect(rememberSource(null, 'card')).toBe('card')
    expect(rememberSource('direct', 'card')).toBe('card')
    expect(rememberSource('card', 'flyer')).toBe('card')
    expect(rememberSource('card', null)).toBe('card')
  })

  it('restores a recent unfinished form only', () => {
    const now = Date.UTC(2026, 9, 19)
    const saved = JSON.stringify({ step: 'photos', answers: {}, otherMake: false, savedAt: now - 1000 })
    expect(loadSaved(saved, now)?.step).toBe('photos')
    expect(loadSaved(saved, now + 8 * 24 * 3600 * 1000)).toBeNull()
    expect(loadSaved('{broken', now)).toBeNull()
    expect(loadSaved(JSON.stringify({ step: 'success', answers: {}, savedAt: now }), now)).toBeNull()
  })
})

describe('number fields', () => {
  const price = step('price').fields[0]

  it('take as many digits as their largest value', () => {
    expect(maxDigits(price)).toBe(String(price.max).length)
    expect(maxDigits({ ...price, max: 50_000_000_000 })).toBe(11)
    expect(maxDigits({ ...price, max: undefined })).toBe(7)
  })
})
