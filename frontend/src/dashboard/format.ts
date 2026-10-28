// Dates and times in the owner's time zone, as the dashboard shows them.

export interface Formatter {
  when(iso: string): string
  date(iso: string, withYear?: boolean): string
  dayKey(date: Date): string
}

export function createFormatter(
  locale: string,
  timeZone: string,
  labels: { today: (time: string) => string; yesterday: (time: string) => string },
): Formatter {
  const time = new Intl.DateTimeFormat(locale, { hour: 'numeric', minute: '2-digit', timeZone })
  const day = new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric', timeZone })
  const dayYear = new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric', year: 'numeric', timeZone })
  // YYYY-MM-DD in the owner's zone, for "is it today" comparisons.
  const key = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone })

  return {
    dayKey: (date) => key.format(date),
    date(iso, withYear = false) {
      const value = new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso)
      return (withYear ? dayYear : day).format(value)
    },
    when(iso) {
      const value = new Date(iso)
      const now = new Date()
      const today = key.format(now)
      const yesterday = key.format(new Date(now.getTime() - 864e5))
      const that = key.format(value)
      if (that === today) return labels.today(time.format(value))
      if (that === yesterday) return labels.yesterday(time.format(value))
      const sameYear = that.slice(0, 4) === today.slice(0, 4)
      return `${(sameYear ? day : dayYear).format(value)}, ${time.format(value)}`
    },
  }
}
