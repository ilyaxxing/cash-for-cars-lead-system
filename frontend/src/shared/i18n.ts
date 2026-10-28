import type { Messages } from './config'

export type Translate = (key: string, params?: Record<string, string | number>) => string

// Text for a dotted key with {placeholders} filled. A missing key renders as
// the key itself: visible on screen, but the page keeps working.
export function createTranslator(messages: Messages): Translate {
  return (key, params = {}) => {
    let node: string | Messages | undefined = messages
    for (const part of key.split('.')) {
      node = typeof node === 'object' ? node[part] : undefined
    }
    if (typeof node !== 'string') return key
    return node.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in params ? String(params[name]) : match,
    )
  }
}
