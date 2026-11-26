// The button next to "Call" in a lead. It follows the way the seller asked
// to be reached: a text (the main channel in the US), an email, a Telegram
// chat (an option a client can add to the preset's contact methods), and
// WhatsApp, as in the design, for a seller who asked for WhatsApp or a call.

import { telegramUsername } from '../shared/telegram'

export interface Reply {
  key: 'sms' | 'email' | 'whatsapp' | 'telegram'
  href: string
}

/** The second button for a lead: `phone` as stored (+14155550142), `email` if given. */
export function reply(method: unknown, phone: string, email = '', subject = '', username?: unknown): Reply {
  const digits = phone.replace(/\D/g, '')
  if (method === 'sms') return { key: 'sms', href: `sms:+${digits}` }
  if (method === 'email' && email) {
    return { key: 'email', href: `mailto:${email}?subject=${encodeURIComponent(subject)}` }
  }
  if (method === 'telegram') {
    const handle = telegramUsername(username)
    return { key: 'telegram', href: `https://t.me/${handle ? handle.slice(1) : '+' + digits}` }
  }
  return { key: 'whatsapp', href: `https://wa.me/${digits}` }
}
