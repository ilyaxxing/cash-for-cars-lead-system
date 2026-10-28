import { afterEach, describe, expect, it, vi } from 'vitest'
import { formatPhone, prepareRegion } from '../shared/region'
import { messenger } from './contact'
import { createFormatter } from './format'

const fmt = createFormatter('en-US', 'America/New_York', {
  today: (time) => `Today, ${time}`,
  yesterday: (time) => `Yesterday, ${time}`,
})

describe('dates in the owner time zone', () => {
  afterEach(() => vi.useRealTimers())

  it('says today and yesterday by the owner calendar, not UTC', () => {
    // 01:30 UTC on Oct 21 is still Oct 20 in New York.
    vi.useFakeTimers({ now: new Date('2026-10-21T01:30:00Z') })
    expect(fmt.when('2026-10-20T22:05:00Z')).toBe('Today, 6:05 PM')
    expect(fmt.when('2026-10-19T15:00:00Z')).toBe('Yesterday, 11:00 AM')
    expect(fmt.when('2026-10-02T15:00:00Z')).toBe('Oct 2, 11:00 AM')
    expect(fmt.when('2025-12-31T15:00:00Z')).toBe('Dec 31, 2025, 10:00 AM')
  })

  it('formats plain dates without shifting the day', () => {
    expect(fmt.date('2026-10-19')).toBe('Oct 19')
  })
})

describe('phone numbers', () => {
  it('reads E.164 US numbers the American way', () => {
    expect(formatPhone('+14155550142')).toBe('(415) 555-0142')
    expect(formatPhone('4155550142')).toBe('(415) 555-0142')
    expect(formatPhone('1-415-555-0142')).toBe('(415) 555-0142')
    expect(formatPhone('415555')).toBe('415555')
    expect(formatPhone('+442079460958')).toBe('+442079460958') // pii-allow: UK drama range
  })

  it("reads another country's numbers the local way", async () => {
    await prepareRegion({ phone_region: 'RU' })
    try {
      expect(formatPhone('+79123456789')).toBe('8 (912) 345-67-89') // pii-allow: fake number
      expect(formatPhone('+442079460958')).toBe('+44 20 7946 0958') // pii-allow: UK drama range
      expect(formatPhone('not a number')).toBe('not a number')
    } finally {
      await prepareRegion({ phone_region: 'US' })
    }
  })
})

describe('messenger button', () => {
  it('opens WhatsApp by default', () => {
    expect(messenger('call', '(415) 555-0142')).toEqual({ key: 'whatsapp', href: 'https://wa.me/4155550142' })
    expect(messenger(undefined, '+1 415 555 0142').href).toBe('https://wa.me/14155550142')
  })

  it('opens Telegram for a seller who asked for it', () => {
    expect(messenger('telegram', '+7 905 555-01-42')).toEqual({ key: 'telegram', href: 'https://t.me/+79055550142' }) // pii-allow (made-up number)
  })
})
