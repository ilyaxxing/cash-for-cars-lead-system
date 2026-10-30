<script lang="ts">
  // The seller form shell: brand bar or progress header, the scrolling step,
  // and the primary action bar. Layout values are the design's two sizes:
  // narrow (phones) and wide (880 px and up).
  import { setContext, tick } from 'svelte'
  import BrandMark from '../shared/BrandMark.svelte'
  import type { AppConfig } from '../shared/config'
  import { REVIEW, SUCCESS, WELCOME } from './engine'
  import Header from './Header.svelte'
  import { enterStep, nudge } from './motion'
  import Photos from './Photos.svelte'
  import Question from './Question.svelte'
  import Review from './Review.svelte'
  import { FormState } from './state.svelte'
  import Success from './Success.svelte'
  import Welcome from './Welcome.svelte'
  import WelcomeBackdrop from './WelcomeBackdrop.svelte'
  import './form.css'

  let { config }: { config: AppConfig } = $props()
  // svelte-ignore state_referenced_locally
  const form = new FormState(config)
  setContext('form', form)
  const t = form.t

  let scrollEl: HTMLDivElement | undefined = $state()
  let stepEl: HTMLDivElement | undefined = $state()
  let buttonEl: HTMLButtonElement | undefined = $state()

  const isWelcome = $derived(form.screen === WELCOME)
  const isSuccess = $derived(form.screen === SUCCESS)
  const isQuestion = $derived(!isWelcome && !isSuccess)
  const isPhotos = $derived(form.step?.fields.some((f) => f.type === 'photos') ?? false)
  const wide = $derived(form.wide)

  const layout = $derived({
    headPad: wide ? '28px 48px 0' : 'max(10px, env(safe-area-inset-top)) 20px 0',
    // The step header keeps a strip below the progress labels, so text
    // scrolled up under it is cut off at a distance, not against the labels.
    stepHeadPad: wide ? '28px 48px 12px' : 'max(10px, env(safe-area-inset-top)) 20px 12px',
    shellMax: wide ? '1180px' : '100%',
    contentMax: wide ? (isWelcome ? '1180px' : '560px') : '100%',
    bodyPad: wide
      ? isWelcome
        ? '20px 48px 56px'
        : isSuccess
          ? '34px 48px 40px'
          : '22px 48px 40px'
      : isWelcome
        ? '0 20px 0'
        : isSuccess
          ? '20px 20px 28px'
          : '8px 20px 28px',
    barPad: wide ? '14px 48px 34px' : '12px 20px max(18px, env(safe-area-inset-bottom))',
    brandPos: !wide && isWelcome ? 'absolute' : 'relative',
  })

  const chips = $derived.by(() => {
    if (!form.step?.show_chips) return []
    const values = form.preset.steps
      .flatMap((step) => step.fields)
      .filter((field) => field.chip)
      .map((field) => form.display(field, form.answers[field.id]))
      .filter(Boolean)
    return values.map((value, index) => ({ value, last: index === values.length - 1 }))
  })

  const primary = $derived.by(() => {
    const step = form.step
    let label = t('form.buttons.continue')
    let arrow = true
    let note = ''
    let show = !isSuccess
    let secondary: { label: string; run: () => void } | null = null
    if (isWelcome) {
      label = t('form.welcome.cta')
      show = !wide
    }
    if (step?.skippable) secondary = { label: t('form.buttons.skip'), run: form.skip }
    if (step?.submit) {
      label = form.busy ? t('form.buttons.saving') : form.saveFailed ? t('form.buttons.try_again') : t('form.buttons.save')
      arrow = !form.busy
      note = form.busy ? '' : t('form.notes.contact')
    }
    if (isPhotos) {
      label = t('form.buttons.to_review')
      secondary = form.donePhotos.length ? null : { label: t('form.buttons.later'), run: form.skip }
    }
    if (form.screen === REVIEW) {
      label = form.busy
        ? t('form.buttons.submitting')
        : form.submitFailed
          ? t('form.buttons.try_again')
          : t('form.buttons.submit')
      arrow = !form.busy
      note = t('form.notes.review')
    }
    if (form.fromReview && step && !step.submit && !isPhotos) label = t('form.buttons.back_to_review')
    return { label, arrow, note, show, secondary }
  })

  // A new step: back to the top, slide in, and on phones focus the first
  // field of steps that are mostly typing.
  $effect(() => {
    const screen = form.screen
    tick().then(() => {
      if (scrollEl) scrollEl.scrollTop = 0
      enterStep(stepEl, form.dir)
      const autofocus = form.step?.fields[0]
      const typing = autofocus && (autofocus.unit === 'currency' || autofocus.format || autofocus.id === 'location')
      if (typing && !wide && screen) {
        setTimeout(() => stepEl?.querySelector<HTMLInputElement>('input')?.focus({ preventScroll: true }), 320)
      }
    })
  })

  $effect(() => {
    if (form.nudges) nudge(buttonEl)
  })

  $effect(() => {
    // Saved after every change of answers or step, so a reload loses nothing.
    void form.answers
    void form.screen
    form.persist()
  })
</script>

<div class="app" bind:clientWidth={form.width}>
  {#if isWelcome && !wide}<WelcomeBackdrop />{/if}
  {#if isWelcome || isSuccess}
    <div class="brand-bar" class:over={!wide && isWelcome} style:padding={layout.headPad} style:position={layout.brandPos}>
      <div class="brand-row" style:max-width={layout.shellMax}>
        <BrandMark brand={config.brand} />
        <a href={config.privacyUrl}>{t('form.privacy_link')}</a>
      </div>
    </div>
  {/if}

  {#if isQuestion}
    <Header pad={layout.stepHeadPad} maxWidth={wide ? '560px' : '100%'} />
  {/if}

  <div class="scroll" bind:this={scrollEl}>
    <div class="content" style:max-width={layout.contentMax} style:padding={layout.bodyPad}>
      {#if chips.length}
        <div class="chips" aria-label={t('form.header.answers_so_far')}>
          {#each chips as chip (chip.value)}
            <span class="chip"><span class="dot" class:last={chip.last}></span>{chip.value}</span>
          {/each}
        </div>
      {/if}

      <div class="step" bind:this={stepEl}>
        {#if isWelcome}
          <Welcome />
        {:else if isSuccess}
          <Success />
        {:else if form.screen === REVIEW}
          <Review />
        {:else if isPhotos}
          <Photos scroller={scrollEl} />
        {:else if form.step}
          {#key form.step.id}
            <Question step={form.step} scroller={scrollEl} />
          {/key}
        {/if}
      </div>
    </div>
  </div>

  {#if primary.show}
    <div class="bar" class:quiet={isWelcome} style:padding={layout.barPad}>
      <div class="bar-inner" style:max-width={layout.contentMax}>
        <button
          bind:this={buttonEl}
          class="primary"
          class:busy={form.busy}
          onclick={form.next}
          disabled={form.busy || form.waitsForAnswer}
          aria-busy={form.busy}
        >
          {#if form.busy}<span aria-hidden="true" class="spinner"></span>{/if}
          <span>{primary.label}</span>
          {#if primary.arrow}
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path
                d="M3.5 9h11M10 4.5L14.5 9 10 13.5"
                style="stroke: var(--on-accent)"
                stroke-width="1.8"
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          {/if}
        </button>
        {#if primary.secondary}
          <button class="secondary" onclick={primary.secondary.run} disabled={form.busy}>{primary.secondary.label}</button>
        {/if}
        {#if primary.note}<div class="note">{primary.note}</div>{/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .app {
    position: relative;
    width: 100%;
    height: 100dvh;
    overflow: hidden;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    isolation: isolate;
  }

  .brand-bar {
    flex: none;
    top: 0;
    left: 0;
    right: 0;
    z-index: 3;
  }

  /* On the phone welcome screen the headline scrolls up under the logo: the
     bar shades it out, much like the picture's own darkening at the top. */
  .brand-bar.over {
    padding-bottom: 18px !important;
    background: linear-gradient(180deg, #111212 0%, #111212 55%, rgba(17, 18, 18, 0) 100%);
  }

  .brand-row {
    margin: 0 auto;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .brand-row a {
    font: 500 13.5px/1 var(--font-sans);
    color: var(--text-muted);
  }

  .scroll {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .content {
    margin: 0 auto;
    box-sizing: border-box;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 22px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 28px;
    padding: 0 10px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--line);
    font: 500 12px/1 var(--font-mono);
    color: #d9d8d2;
    animation: ui-chip 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .chip .dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--line-hover);
  }

  .chip .dot.last {
    background: var(--accent);
  }

  .bar {
    flex: none;
    background: var(--bg);
    border-top: 1px solid #1f2121;
  }

  .bar.quiet {
    border-top-color: transparent;
  }

  .bar-inner {
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .primary {
    height: 58px;
    border: 0;
    border-radius: 16px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 17px/1 var(--font-sans);
    letter-spacing: -0.01em;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .primary:hover {
    background: var(--accent-hover);
  }

  .primary:active {
    transform: scale(0.98);
  }

  .primary.busy {
    background: var(--accent-pressed);
  }

  /* An optional step with no answer yet: Skip for now is the way on. */
  .primary:disabled:not(.busy) {
    opacity: 0.35;
    cursor: default;
  }

  .primary:disabled:not(.busy):hover {
    background: var(--accent);
  }

  .primary:disabled:not(.busy):active {
    transform: none;
  }

  .spinner {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid rgb(var(--on-accent-rgb) / 0.25);
    border-top-color: var(--on-accent);
    animation: ui-spin 0.7s linear infinite;
  }

  .secondary {
    height: 44px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    color: var(--text);
    font: 500 15px/1 var(--font-sans);
    cursor: pointer;
  }

  .secondary:hover {
    background: var(--surface);
  }

  .note {
    min-height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    font: 400 12.5px/1.4 var(--font-sans);
    color: var(--text-muted);
  }
</style>
