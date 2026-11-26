/** Accept a username or a public profile link and keep only the handle. */
export function telegramUsername(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const match = /^(?:(?:https?:\/\/)?t\.me\/([a-z][a-z0-9_]{0,31})\/?|@?([a-z][a-z0-9_]{0,31}))$/i.exec(value.trim())
  return match ? '@' + (match[1] || match[2]) : undefined
}
