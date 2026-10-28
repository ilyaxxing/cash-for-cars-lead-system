// The messenger button next to "Call" in a lead. WhatsApp, as in the design;
// Telegram instead for a seller who asked to be reached there (an option a
// client can add to the preset's contact methods). Both open a chat by
// phone number.

export interface Messenger {
  key: 'whatsapp' | 'telegram'
  href: string
}

export function messenger(method: unknown, phone: string): Messenger {
  const digits = phone.replace(/\D/g, '')
  if (method === 'telegram') {
    return { key: 'telegram', href: `https://t.me/+${digits}` }
  }
  return { key: 'whatsapp', href: `https://wa.me/${digits}` }
}
