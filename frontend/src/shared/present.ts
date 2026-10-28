// How preset answers read on screen, shared by the seller form and the
// dashboard so a value looks the same in both: "78,400 mi", "$21,500",
// "Before 1990", "Don't know". Numbers and prices follow the client's
// country: "850 000 ₽" in Russia.

import type { AppConfig, FieldSpec } from './config'
import { createTranslator, type Translate } from './i18n'
import { formatPhone } from './region'

export type AnswerValue = string | number | undefined

export const EARLIER = 'earlier'

export interface Presenter {
  t: Translate
  numberLocale: string
  currencySymbol: string
  // The symbol follows the amount ("850 000 ₽") rather than leading it.
  currencyAfter: boolean
  fields: FieldSpec[]
  formatNumber(value: number): string
  formatMoney(value: number): string
  // Case changes by the language's rules: Turkish "i" capitalizes to "İ".
  lower(text: string): string
  upper(text: string): string
  unit(kind: 'short' | 'long'): string
  findField(id: string): FieldSpec | undefined
  fieldLabel(field: FieldSpec, place?: 'form' | 'review'): string
  display(field: FieldSpec, value: AnswerValue): string
}

function isBlank(value: AnswerValue): boolean {
  return value === undefined || value === null || (typeof value === 'string' && !value.trim())
}

export function createPresenter(config: AppConfig): Presenter {
  const t = createTranslator(config.messages)
  const numberLocale = `${config.locale}-${config.preset.phone_region}`
  const number = new Intl.NumberFormat(numberLocale)
  const money = new Intl.NumberFormat(numberLocale, {
    style: 'currency',
    currency: config.currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })
  const parts = money.formatToParts(0)
  const symbolAt = parts.findIndex((part) => part.type === 'currency')
  const currencySymbol = parts[symbolAt]?.value ?? config.currency
  const currencyAfter = symbolAt > parts.findIndex((part) => part.type === 'integer')
  const fields = config.preset.steps.flatMap((step) =>
    step.fields.flatMap((field) => [field, ...(field.follow_up?.fields ?? [])]),
  )

  const formatNumber = (value: number) => number.format(value)
  const formatMoney = (value: number) => money.format(value)
  const unit = (kind: 'short' | 'long') => t(`units.${config.preset.distance_unit}.${kind}`)

  return {
    t,
    numberLocale,
    currencySymbol,
    currencyAfter,
    fields,
    formatNumber,
    formatMoney,
    lower: (text) => text.toLocaleLowerCase(numberLocale),
    upper: (text) => text.toLocaleUpperCase(numberLocale),
    unit,
    findField: (id) => fields.find((field) => field.id === id),
    fieldLabel(field, place = 'form') {
      if (place === 'review') {
        const review = t(`preset.fields.${field.id}.review_label`)
        if (!review.startsWith('preset.')) return review
      }
      return t(`preset.fields.${field.id}.label`)
    },
    display(field, value) {
      if (isBlank(value)) return ''
      switch (field.type) {
        case 'select':
          return t(`preset.options.${field.id}.${value}.label`)
        case 'yes_no':
          return t(`preset.yes_no.${value}`)
        case 'number': {
          if (value === EARLIER) return t(`preset.fields.${field.id}.earlier_value`, { year: field.earlier ?? '' })
          const amount = typeof value === 'number' ? value : Number(String(value).replace(/\D/g, ''))
          if (field.unit === 'currency') return formatMoney(amount)
          if (field.unit === 'distance') return `${formatNumber(amount)} ${unit('short')}`
          return String(amount)
        }
        case 'phone':
          return formatPhone(String(value))
        default:
          return String(value)
      }
    },
  }
}
