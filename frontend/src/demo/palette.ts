// A business's color for the demo (a link with ?color=ff8a00), worked out as
// app/branding/colors.py does for BRAND_COLOR, so the demo shows exactly the
// colors that business's own instance would.

type RGB = [number, number, number]

const BACKGROUND: RGB = [17, 18, 18]
const DARK: RGB = [17, 18, 18]
const LIGHT: RGB = [255, 255, 255]
const MIN_CONTRAST = 3

function luminance(rgb: RGB): number {
  const [r, g, b] = rgb.map((channel) => {
    const value = channel / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(first: RGB, second: RGB): number {
  const [light, dark] = [luminance(first), luminance(second)].sort((x, y) => y - x)
  return (light + 0.05) / (dark + 0.05)
}

// Python's round(): halves go to the even neighbour.
function round(value: number): number {
  const nearest = Math.round(value)
  return Math.abs(value % 1) === 0.5 && nearest % 2 !== 0 ? nearest - 1 : nearest
}

function mix(color: RGB, other: RGB, share: number): RGB {
  return color.map((channel, i) => round(channel + (other[i] - channel) * share)) as RGB
}

const hex = (rgb: RGB) => `#${rgb.map((c) => c.toString(16).padStart(2, '0')).join('')}`.toUpperCase()
const channels = (rgb: RGB) => rgb.join(' ')

// The CSS variables for a color, or null when it is not one or is too dark
// to read on the app's dark screens (the instance refuses it the same way).
export function accentVariables(value: string): Record<string, string> | null {
  const match = /^#?([0-9a-fA-F]{6})$/.exec(value.trim())
  if (!match) return null
  const number = parseInt(match[1], 16)
  const accent: RGB = [(number >> 16) & 255, (number >> 8) & 255, number & 255]
  if (contrast(accent, BACKGROUND) < MIN_CONTRAST) return null
  const onAccent = contrast(accent, DARK) >= contrast(accent, LIGHT) ? DARK : LIGHT
  return {
    '--accent': hex(accent),
    '--accent-rgb': channels(accent),
    '--accent-hover': hex(mix(accent, LIGHT, 0.2)),
    '--accent-pressed': hex(mix(accent, [0, 0, 0], 0.09)),
    '--on-accent': hex(onAccent),
    '--on-accent-rgb': channels(onAccent),
  }
}
