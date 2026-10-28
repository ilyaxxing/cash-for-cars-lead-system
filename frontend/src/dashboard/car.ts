// The car summary shared by lead cards and the lead panel: title, year and
// mileage line, price, condition and VIN, all read through the preset.

import type { FieldSpec } from '../shared/config'
import type { Presenter } from '../shared/present'
import type { Card } from './api'

export interface CarSummary {
  title: string
  sub: string
  price: string
  conditionField?: FieldSpec
  condition: string
  vinField?: FieldSpec
  vin: string
}

export function summarize(present: Presenter, lead: Card): CarSummary {
  const show = (id: string) => {
    const field = present.findField(id)
    return field ? present.display(field, lead.answers[id]) : ''
  }
  const conditionField = present.fields.find(
    (field) => field.type === 'select' && field.options.some((option) => option.level !== undefined),
  )
  const vinField = present.fields.find((field) => field.format === 'vin')
  return {
    title: [lead.answers.make, lead.answers.model].filter(Boolean).join(' '),
    sub: [show('year'), show('mileage')].filter(Boolean).join(' · '),
    price: show('asking_price'),
    conditionField,
    condition: conditionField ? present.display(conditionField, lead.answers[conditionField.id]) : '',
    vinField,
    vin: vinField ? String(lead.answers[vinField.id] ?? '') : '',
  }
}
