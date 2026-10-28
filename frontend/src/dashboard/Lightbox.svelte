<script lang="ts">
  // Full-screen photo viewer with arrows, keyboard navigation and zoom.
  import { getContext } from 'svelte'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t

  const photos = $derived(dash.detail?.photos ?? [])
  const index = $derived(dash.lightbox ?? 0)
  const photo = $derived(photos[index])

  function label(i: number): string {
    const item = photos[i]
    if (item?.slot) return t(`preset.photos.${item.slot}.label`)
    return t('dashboard.lead.extra_photo', { n: photos.slice(0, i + 1).filter((p) => !p.slot).length })
  }

  function move(step: number, event?: Event) {
    event?.stopPropagation()
    dash.lightbox = (index + step + photos.length) % photos.length
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'ArrowRight') move(1)
    if (event.key === 'ArrowLeft') move(-1)
  }

  // Zoom like Instagram: pinch with two fingers to look closer; the photo
  // follows the fingers and may grow past its frame. Lift one finger and the
  // other keeps holding and moving it; it springs back only when no finger is
  // left. The page itself never zooms (shared/noZoom.ts). With a mouse, a
  // double click zooms in on a spot and back out.
  interface Point {
    x: number
    y: number
  }

  const MAX_SCALE = 4
  const CLICK_SCALE = 2.5
  let frame: HTMLDivElement | undefined = $state()
  let scale = $state(1)
  let shiftX = $state(0)
  let shiftY = $state(0)
  let originX = $state(50)
  let originY = $state(50)
  let pinching = $state(false)
  // Drawn above the controls while zoomed or springing back.
  let lifted = $state(false)
  // The gesture so far: where the fingers started from, and the zoom and
  // shift at that moment, so a finger lifted or added changes nothing.
  let grip: { start: Point; distance: number; scale: number; x: number; y: number } | null = null
  let lastTouch = 0
  let settleTimer: ReturnType<typeof setTimeout> | undefined

  // Every photo opens at full view.
  $effect(() => {
    void index
    resetZoom()
  })

  function resetZoom() {
    scale = 1
    shiftX = 0
    shiftY = 0
    // Back under the controls once the spring-back is over. A timer, not
    // transitionend: with reduced motion there is no transition to end.
    clearTimeout(settleTimer)
    settleTimer = setTimeout(() => {
      if (scale === 1 && !pinching) lifted = false
    }, 300)
  }

  // Zoom around this point of the frame.
  function originAt(at: Point) {
    if (!frame) return
    const box = frame.getBoundingClientRect()
    originX = ((at.x - box.left) / box.width) * 100
    originY = ((at.y - box.top) / box.height) * 100
  }

  const point = (touch: Touch): Point => ({ x: touch.clientX, y: touch.clientY })
  const middle = (a: Touch, b: Touch): Point => ({ x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 })
  const distance = (a: Touch, b: Touch) => Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY)

  // Start (or restart, when a finger comes or goes) from the current zoom.
  function takeHold(touches: TouchList) {
    if (touches.length >= 2) {
      const [a, b] = [touches[0], touches[1]]
      grip = { start: middle(a, b), distance: distance(a, b), scale, x: shiftX, y: shiftY }
    } else if (touches.length === 1) {
      grip = { start: point(touches[0]), distance: 0, scale, x: shiftX, y: shiftY }
    }
  }

  function onTouchStart(event: TouchEvent) {
    lastTouch = Date.now()
    if (event.touches.length >= 2) {
      event.preventDefault()
      if (!pinching) {
        // A new pinch zooms around the point between the fingers.
        const [a, b] = [event.touches[0], event.touches[1]]
        resetZoom()
        originAt(middle(a, b))
        pinching = true
        lifted = true
      }
      takeHold(event.touches)
    } else if (pinching) {
      takeHold(event.touches)
    }
  }

  function onTouchMove(event: TouchEvent) {
    if (!pinching || !grip) return
    event.preventDefault()
    const touches = event.touches
    if (touches.length >= 2) {
      const [a, b] = [touches[0], touches[1]]
      const at = middle(a, b)
      scale = Math.min(MAX_SCALE, Math.max(1, (grip.scale * distance(a, b)) / grip.distance))
      shiftX = grip.x + at.x - grip.start.x
      shiftY = grip.y + at.y - grip.start.y
    } else if (touches.length === 1) {
      const at = point(touches[0])
      shiftX = grip.x + at.x - grip.start.x
      shiftY = grip.y + at.y - grip.start.y
    }
  }

  function onTouchEnd(event: TouchEvent) {
    if (!pinching) return
    if (event.touches.length > 0) {
      // One finger lifted: the others keep holding the photo where it is.
      takeHold(event.touches)
      return
    }
    // No finger left: spring back to full view.
    grip = null
    pinching = false
    resetZoom()
  }

  function onDoubleClick(event: MouseEvent) {
    // Touch screens zoom by pinching only.
    if (Date.now() - lastTouch < 600) return
    if (scale > 1) return resetZoom()
    originAt({ x: event.clientX, y: event.clientY })
    lifted = true
    scale = CLICK_SCALE
  }

  // Touch listeners that may cancel scrolling must not be passive.
  function zoomable(node: HTMLElement) {
    const options = { passive: false }
    node.addEventListener('touchstart', onTouchStart, options)
    node.addEventListener('touchmove', onTouchMove, options)
    node.addEventListener('touchend', onTouchEnd)
    node.addEventListener('touchcancel', onTouchEnd)
    return {
      destroy() {
        node.removeEventListener('touchstart', onTouchStart)
        node.removeEventListener('touchmove', onTouchMove)
        node.removeEventListener('touchend', onTouchEnd)
        node.removeEventListener('touchcancel', onTouchEnd)
      },
    }
  }
</script>

<svelte:window onkeydown={onKey} />

<div role="dialog" aria-modal="true" aria-label={t('dashboard.lead.preview')} class="lightbox">
  <div class="top">
    <span class="caption">
      <span class="label">{t('dashboard.lead.photo_tag', { n: String(index + 1).padStart(2, '0'), label: label(index) })}</span>
      <span>{index + 1} / {photos.length}</span>
    </span>
    <button class="close" aria-label={t('dashboard.lead.close_preview')} onclick={() => (dash.lightbox = null)}>
      <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="#F4F3EE" stroke-width="1.6" stroke-linecap="round" /></svg>
    </button>
  </div>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="stage" style:padding="0 {dash.desk ? '76px' : '12px'} 28px" onclick={() => (dash.lightbox = null)}>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div
      bind:this={frame}
      class="frame"
      class:lifted
      data-zoomable
      use:zoomable
      onclick={(event) => event.stopPropagation()}
      ondblclick={onDoubleClick}
    >
      {#if photo}
        <img
          src={photo.url}
          alt={label(index)}
          class:pinching
          style:transform-origin="{originX}% {originY}%"
          style:transform="translate({shiftX}px, {shiftY}px) scale({scale})"
          draggable="false"
        />
      {/if}
    </div>
    {#if photos.length > 1}
      <button class="arrow" style:left={dash.desk ? '16px' : '10px'} aria-label={t('dashboard.lead.previous_photo')} onclick={(event) => move(-1, event)}>
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M12.5 4.5L7 10l5.5 5.5" stroke="#F4F3EE" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      <button class="arrow" style:right={dash.desk ? '16px' : '10px'} aria-label={t('dashboard.lead.next_photo')} onclick={(event) => move(1, event)}>
        <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M7.5 4.5L13 10l-5.5 5.5" stroke="#F4F3EE" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
    {/if}
  </div>
</div>

<style>
  .lightbox {
    position: absolute;
    inset: 0;
    z-index: 40;
    display: flex;
    flex-direction: column;
    /* Solid: at 95% the lead's text ghosted through around the photo. */
    background: #060707;
    animation: ui-fade 0.18s both;
    padding-top: env(safe-area-inset-top);
  }

  .top {
    flex: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    height: 64px;
    padding: 0 16px 0 22px;
  }

  .caption {
    display: flex;
    gap: 14px;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .label {
    color: var(--text);
  }

  .close {
    width: 44px;
    height: 44px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .close:hover,
  .arrow:hover {
    background: var(--surface);
  }

  .stage {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .frame {
    position: relative;
    width: 100%;
    max-width: 1200px;
    max-height: 100%;
    aspect-ratio: 3 / 2;
    border-radius: 10px;
    overflow: hidden;
    background: var(--surface);
    animation: ui-pop-in 0.22s cubic-bezier(0.2, 0.8, 0.2, 1) both;
    /* The photo's own gestures replace the browser's. */
    touch-action: none;
  }

  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
    user-select: none;
    -webkit-user-select: none;
  }

  /* Follow the fingers directly while they move. */
  img.pinching {
    transition: none;
  }

  /* Zoomed, the photo may grow past its frame and over the controls. */
  .frame.lifted {
    overflow: visible;
    z-index: 5;
  }

  .arrow {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 44px;
    height: 44px;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(17, 18, 18, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }
</style>
