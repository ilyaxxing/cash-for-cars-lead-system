import { describe, expect, it } from 'vitest'
import type { AppConfig } from './config'
import { createPresenter } from './present'

function config(locale: string, region: string, currency: string): AppConfig {
  return {
    locale,
    currency,
    messages: {},
    preset: { phone_region: region, distance_unit: 'mi', steps: [] },
  } as unknown as AppConfig
}

describe('prices', () => {
  it('lead with the symbol in the US', () => {
    const present = createPresenter(config('en', 'US', 'USD'))
    expect(present.formatMoney(21500)).toBe('$21,500')
    expect(present.currencyAfter).toBe(false)
  })

  it('follow the amount where the country writes them so', () => {
    const present = createPresenter(config('ru', 'RU', 'RUB'))
    expect(present.formatMoney(850000)).toBe('850 000 ₽')
    expect(present.currencySymbol).toBe('₽')
    expect(present.currencyAfter).toBe(true)
  })
})
