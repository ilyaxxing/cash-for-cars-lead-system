// Small animations from the design prototype, all skipped for people who
// asked their system for reduced motion.

const reduced = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
const EASE = 'cubic-bezier(.2,.8,.2,1)'

// A tap on an option: a short squeeze and release.
export function pulse(event: Event) {
  const element = event.currentTarget as HTMLElement | null
  if (!element?.animate || reduced()) return
  element.animate([{ transform: 'scale(.96)' }, { transform: 'scale(1.01)' }, { transform: 'scale(1)' }], {
    duration: 220,
    easing: EASE,
  })
}

// The primary button shakes when the step cannot be left yet.
export function nudge(element: HTMLElement | undefined) {
  if (!element?.animate || reduced()) return
  element.animate(
    [
      { transform: 'translateX(0)' },
      { transform: 'translateX(-6px)' },
      { transform: 'translateX(5px)' },
      { transform: 'translateX(-2px)' },
      { transform: 'translateX(0)' },
    ],
    { duration: 280, easing: 'ease-out' },
  )
}

// A new step slides in from the direction of travel and its parts follow
// one by one (elements marked with data-st).
export function enterStep(element: HTMLElement | undefined, direction: number) {
  if (!element?.animate || reduced()) return
  element.animate([{ opacity: 0, transform: `translateX(${direction * 20}px)` }, { opacity: 1, transform: 'none' }], {
    duration: 260,
    easing: EASE,
  })
  element.querySelectorAll<HTMLElement>('[data-st]').forEach((child, index) => {
    if (index > 14) return
    child.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], {
      duration: 260,
      delay: 40 + index * 22,
      easing: EASE,
      fill: 'backwards',
    })
  })
}

// Bring an element into view inside the scrolling step with as little
// movement as possible: nothing at all when it is already fully visible,
// otherwise just enough to clear the bottom edge (the on-screen keyboard
// included) without pushing its top out. Pulling every focused field up to
// the top made the screen jump on each tap.
export function reveal(element: HTMLElement, container: HTMLElement | undefined, margin = 24) {
  if (!container) return
  const rect = element.getBoundingClientRect()
  const box = container.getBoundingClientRect()
  const view = window.visualViewport
  const visibleBottom = view ? Math.min(box.bottom, view.offsetTop + view.height) : box.bottom
  let delta = 0
  if (rect.bottom > visibleBottom - margin) delta = rect.bottom - (visibleBottom - margin)
  if (rect.top - delta < box.top + margin) delta = rect.top - (box.top + margin)
  if (Math.abs(delta) > 2) container.scrollBy({ top: delta, behavior: reduced() ? 'auto' : 'smooth' })
}

// Keep a focused field clear of the on-screen keyboard: wait until the
// keyboard has opened (the visual viewport shrinks), then reveal the field.
export function scrollIntoView(input: HTMLElement, container: HTMLElement | undefined) {
  if (!container) return
  const view = window.visualViewport
  let settled = false
  const settle = () => {
    if (settled) return
    settled = true
    view?.removeEventListener('resize', settle)
    reveal(input, container)
  }
  view?.addEventListener('resize', settle)
  // No resize when the keyboard was already open, or on a desktop.
  setTimeout(settle, 350)
}
