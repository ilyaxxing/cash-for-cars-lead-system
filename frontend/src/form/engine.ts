// The seller form's logic, kept free of the DOM so it can be unit-tested.
//
// Screens come from the preset: welcome, every enabled step, review, success.
// Validation mirrors app/services/answers.py and returns the same error codes;
// the server checks everything again, this only spares the seller a round trip.

import type { FieldSpec, Preset, Step } from '../shared/config'
import { isPostalCode, normalizePhone } from '../shared/region'

export type Value = string | number
export type Answers = Record<string, Value | undefined>
export interface FieldError {
  code: string
  params?: Record<string, string | number>
}
export type Errors = Record<string, FieldError>

export const EARLIER = 'earlier'
export const WELCOME = 'welcome'
export const REVIEW = 'review'
export const SUCCESS = 'success'

// --- screens and progress -----------------------------------------------------

export function activeSteps(preset: Preset): Step[] {
  return preset.steps.filter((step) => step.enabled)
}

export function screenIds(preset: Preset): string[] {
  return [WELCOME, ...activeSteps(preset).map((step) => step.id), REVIEW, SUCCESS]
}

export function stepById(preset: Preset, id: string): Step | undefined {
  return activeSteps(preset).find((step) => step.id === id)
}

export function submitStep(preset: Preset): Step {
  return activeSteps(preset).find((step) => step.submit)!
}

export interface Progress {
  n: number
  total: number
  segments: number[]
  remainingSeconds: number
  last: boolean
}

// Numbered like the design: welcome is 1, review is the last ("12 of 12"),
// success is not counted. Each answered step fills a segment; the current
// one shows as a partial bar.
export function progress(ids: string[], current: string): Progress {
  const index = ids.indexOf(current)
  const total = ids.length - 1
  const segments = Array.from({ length: total - 1 }, (_, i) =>
    i < index - 1 ? 1 : i === index - 1 ? 0.45 : 0,
  )
  return {
    n: index + 1,
    total,
    segments,
    remainingSeconds: (total - index) * 18,
    last: index === total - 1,
  }
}

// --- fields -------------------------------------------------------------------

export function isEmpty(value: Value | undefined): boolean {
  return value === undefined || value === null || (typeof value === 'string' && !value.trim())
}

export function optionIds(field: FieldSpec): string[] {
  if (field.type === 'yes_no') return ['yes', 'no', ...(field.unknown ? ['unknown'] : [])]
  return field.options.map((option) => option.id)
}

// Fields of a step including the follow-ups its current answers unlock.
export function visibleFields(step: Step, answers: Answers): FieldSpec[] {
  const result: FieldSpec[] = []
  for (const field of step.fields) {
    result.push(field)
    if (field.follow_up && answers[field.id] === field.follow_up.when) {
      result.push(...field.follow_up.fields)
    }
  }
  return result
}

function allStepFields(step: Step): FieldSpec[] {
  return step.fields.flatMap((field) => [field, ...(field.follow_up?.fields ?? [])])
}

export function isStepBlank(step: Step, answers: Answers): boolean {
  return step.fields.every((field) => field.type === 'photos' || isEmpty(answers[field.id]))
}

// Skipping a step forgets whatever was typed there.
export function clearStep(step: Step, answers: Answers): Answers {
  const next = { ...answers }
  for (const field of allStepFields(step)) delete next[field.id]
  return next
}

export function suggestionsFor(field: FieldSpec, answers: Answers): string[] {
  if (Array.isArray(field.suggestions)) return field.suggestions
  const key = field.suggestions_by ? answers[field.suggestions_by] : undefined
  return typeof key === 'string' ? (field.suggestions[key] ?? []) : []
}

// Year grid: the most recent `recent` years first, older ones on request,
// and everything before `earlier` as one answer. Next model year included,
// as on the server.
export function yearOptions(field: FieldSpec, today: Date): { recent: number[]; older: number[] } {
  const top = today.getFullYear()
  const bottom = field.earlier ?? field.min ?? top - 30
  const recentCount = field.recent ?? 12
  const years: number[] = []
  for (let year = top; year >= bottom; year--) years.push(year)
  return { recent: years.slice(0, recentCount), older: years.slice(recentCount) }
}

// --- normalizers (same rules as app/services/validation.py) ----------------------

export function digitsOnly(raw: string, maxDigits = 9): string {
  return raw.replace(/\D/g, '').slice(0, maxDigits)
}

// How many digits a number field takes: as many as its largest value, so a
// price can run to ₩50,000,000 or 5,000,000,000 ₫ where the form allows it.
export function maxDigits(field: FieldSpec): number {
  return String(field.max ?? 9_999_999).length
}

export function parseIntStrict(raw: Value): number | null {
  if (typeof raw === 'number') return Number.isInteger(raw) && raw >= 0 ? raw : null
  const digits = raw.replace(/[\s,_]/g, '')
  return /^\d+$/.test(digits) ? Number(digits) : null
}

export function cleanVin(raw: string): string {
  return raw.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 17)
}

export function vinError(raw: string): FieldError | null {
  const value = raw.replace(/[\s-]/g, '').toUpperCase()
  if (value.length !== 17) return { code: 'length', params: { count: value.length } }
  if (!/^[A-HJ-NPR-Z0-9]{17}$/.test(value)) return { code: 'format' }
  return null
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

// --- validation ---------------------------------------------------------------

function fieldError(field: FieldSpec, value: Value, today: Date): FieldError | null {
  switch (field.type) {
    case 'text': {
      const text = String(value).trim()
      const limit = field.max_length ?? (field.multiline ? 1000 : 200)
      if (text.length > limit) return { code: 'too_long', params: { max: limit } }
      if (field.format === 'vin') return vinError(text)
      if (field.format === 'email' && !EMAIL_RE.test(text)) return { code: 'format' }
      if (field.format === 'postal_code' && !isPostalCode(text)) return { code: 'format' }
      return null
    }
    case 'number': {
      if (field.earlier !== undefined && value === EARLIER) return null
      const number = parseIntStrict(value)
      if (number === null) return { code: 'format' }
      const low = field.earlier ?? field.min
      const high = field.widget === 'year_grid' ? today.getFullYear() + 1 : field.max
      const params = { value: number, min: low ?? '', max: high ?? '' }
      if (low !== undefined && number < low) return { code: 'min', params }
      if (high !== undefined && number > high) return { code: 'max', params }
      return null
    }
    case 'select':
    case 'yes_no':
      return optionIds(field).includes(String(value)) ? null : { code: 'option' }
    case 'phone':
      return normalizePhone(String(value)) ? null : { code: 'format' }
    default:
      return null
  }
}

export function validateStep(step: Step, answers: Answers, today = new Date()): Errors {
  const errors: Errors = {}
  if (step.skippable && isStepBlank(step, answers)) return errors
  for (const field of visibleFields(step, answers)) {
    if (field.type === 'photos') continue
    const value = answers[field.id]
    if (isEmpty(value)) {
      const conditional = Object.entries(field.required_when ?? {}).some(
        ([other, expected]) => answers[other] === expected,
      )
      if ((field.required || conditional) && field.default === undefined) {
        errors[field.id] = { code: 'required' }
      }
      continue
    }
    const error = fieldError(field, value!, today)
    if (error) errors[field.id] = error
  }
  return errors
}

// Answers as the API expects them: every answered field up to the submit
// step, follow-ups only when unlocked, numbers as numbers, defaults filled.
export function payload(preset: Preset, answers: Answers): Record<string, Value> {
  const result: Record<string, Value> = {}
  const steps = activeSteps(preset)
  for (const step of steps.slice(0, steps.indexOf(submitStep(preset)) + 1)) {
    for (const field of visibleFields(step, answers)) {
      let value = answers[field.id]
      if (isEmpty(value)) {
        if (field.default !== undefined) result[field.id] = field.default
        continue
      }
      if (field.type === 'number' && value !== EARLIER) value = parseIntStrict(value!) ?? value
      if (typeof value === 'string') value = value.trim()
      result[field.id] = value!
    }
  }
  return result
}

// --- lead source --------------------------------------------------------------

const SOURCE_RE = /^[A-Za-z0-9_-]{1,64}$/

export function parseSource(raw: string | null): string | null {
  const candidate = raw?.trim()
  return candidate && SOURCE_RE.test(candidate) ? candidate.toLowerCase() : null
}

// First meaningful source wins: a label only replaces nothing or "direct".
export function rememberSource(stored: string | null, incoming: string | null): string | null {
  if (incoming && (!stored || stored === 'direct')) return incoming
  return stored
}

// --- saved progress on the seller's device ------------------------------------

export const SAVE_KEY = 'car-buyout-inquiry'
export const SOURCE_KEY = 'car-buyout-source'
export const SAVE_TTL_MS = 7 * 24 * 60 * 60 * 1000

export interface Saved {
  step: string
  answers: Answers
  otherMake: boolean
  leadId?: number
  token?: string
  savedAt: number
}

export function loadSaved(raw: string | null, now: number): Saved | null {
  if (!raw) return null
  try {
    const saved = JSON.parse(raw) as Saved
    if (!saved.step || saved.step === WELCOME || saved.step === SUCCESS) return null
    if (now - saved.savedAt > SAVE_TTL_MS) return null
    return saved
  } catch {
    return null
  }
}
