// The business a demo link is shown to: ?name=Rapid+Cash+Cars&color=ff8a00.
// The demo apps, the policy page and the page for car buyers (docs/for-buyers)
// all read it here, and wear the color the way an instance wears BRAND_COLOR.

import { accentVariables } from './palette'

const MAX_NAME = 40

export interface Business {
  name: string | null
  colors: Record<string, string> | null
  // The two again, for links to the other demo pages.
  query: string
}

export function business(): Business {
  const params = new URLSearchParams(location.search)
  const name = (params.get('name') ?? '').replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, MAX_NAME) || null
  const colors = accentVariables(params.get('color') ?? '')
  const kept = new URLSearchParams()
  if (name) kept.set('name', name)
  if (colors) kept.set('color', colors['--accent'].slice(1))
  return { name, colors, query: kept.toString() ? `?${kept}` : '' }
}

// The same variables the server puts into every page from BRAND_COLOR.
export function wear(colors: Record<string, string>) {
  let style = document.getElementById('brand-colors')
  if (!style) {
    style = document.createElement('style')
    style.id = 'brand-colors'
    document.head.append(style)
  }
  style.textContent = `:root:root{${Object.entries(colors).map(([name, value]) => `${name}:${value}`).join(';')}}`
}
