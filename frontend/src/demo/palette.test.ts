import { describe, expect, it } from 'vitest'
import { accentVariables } from './palette'

// Expected values come from app/branding/colors.py (Palette.css_variables).
describe('a business color in the demo', () => {
  it.each([
    ['#C7F747', '#D2F96C', '#B5E141', '#111212'],
    ['ff8a00', '#FFA133', '#E87E00', '#111212'],
    ['#3DA5FF', '#64B7FF', '#3896E8', '#111212'],
    // 136.5 rounds to the even 136, as Python rounds it.
    ['#969696', '#ABABAB', '#888888', '#111212'],
    ['#E5322D', '#EA5B57', '#D02E29', '#FFFFFF'],
  ])('%s matches the server', (color, hover, pressed, onAccent) => {
    const css = accentVariables(color)!
    expect(css['--accent']).toBe(`#${color.replace('#', '').toUpperCase()}`)
    expect(css['--accent-hover']).toBe(hover)
    expect(css['--accent-pressed']).toBe(pressed)
    expect(css['--on-accent']).toBe(onAccent)
  })

  it('refuses what an instance refuses: not a color, or too dark to read', () => {
    expect(accentVariables('orange')).toBeNull()
    expect(accentVariables('#5A3D8C')).toBeNull()
    expect(accentVariables('#1a1a1a')).toBeNull()
  })
})
