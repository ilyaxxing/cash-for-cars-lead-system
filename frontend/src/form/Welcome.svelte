<script lang="ts">
  // First screen: hero photo, headline, three claims, how it works, and a
  // link back into an unfinished inquiry saved on this device.
  import { getContext } from 'svelte'
  import { hero } from './illustrations'
  import type { FormState } from './state.svelte'

  const form = getContext<FormState>('form')
  const t = form.t

  const claims = t('form.welcome.claims')
    .split(/(?<=\.)\s+/)
    .map((claim) => claim.trim().replace(/\.$/, ''))
    .filter(Boolean)
  const steps = [1, 2, 3].map((n) => ({
    n: `0${n}`,
    title: t(`form.welcome.steps.${n}.title`),
    text: t(`form.welcome.steps.${n}.text`),
  }))

  const resumeLabel = $derived.by(() => {
    const saved = form.saved
    if (!saved) return ''
    const car = typeof saved.answers.make === 'string' && saved.answers.make ? saved.answers.make : t('form.welcome.saved_car')
    const n = form.ids.indexOf(saved.step) + 1
    const label = t('form.welcome.saved_label', { car, n, total: form.ids.length - 1 })
    return t('form.welcome.resume', { label })
  })

  // How far the text has been scrolled up over the car, 0..1. The panel uses
  // it to darken the car behind its first lines: at rest the picture looks
  // exactly as designed, once scrolled the text stays readable.
  function lift(node: HTMLElement) {
    const scroller = node.closest('.scroll')
    if (!scroller) return
    const update = () => node.style.setProperty('--lift', String(Math.min(scroller.scrollTop / 60, 1)))
    scroller.addEventListener('scroll', update, { passive: true })
    update()
    return { destroy: () => scroller.removeEventListener('scroll', update) }
  }
</script>

{#snippet claimList()}
  <!-- Every claim carries its dot: when the list wraps on a narrow phone,
       each line still starts the same way. -->
  <div class="claims">
    {#each claims as claim (claim)}
      <span class="claim"><span aria-hidden="true" class="sep"></span>{claim}</span>
    {/each}
  </div>
{/snippet}

{#if !form.wide}
  <!-- The car is a still backdrop behind the scrolling area (see
       WelcomeBackdrop, drawn by Form), and so is the headline on it: only the
       text below moves, and its panel covers both as it rises. -->
  <div class="narrow">
    <div class="front">
      <div aria-hidden="true" class="stage"></div>
      <div class="panel" use:lift>
        <p data-st class="tagline">{t('form.welcome.tagline')}</p>
        <div data-st>{@render claimList()}</div>
        <ol data-st aria-label={t('form.welcome.how_it_works')} class="how">
          {#each steps as step (step.n)}
            <li>
              <span class="how-n">{step.n}</span>
              <span class="how-body">
                <span class="how-title">{step.title}</span>
                <span class="how-text">{step.text}</span>
              </span>
            </li>
          {/each}
        </ol>
        {#if resumeLabel}
          <button class="resume" onclick={form.resume}>{resumeLabel}</button>
        {/if}
      </div>
    </div>
  </div>
{:else}
  <div class="wide">
    <div data-st class="wide-hero">
      {#if form.config.brand.photo}
        <img src={form.config.brand.photo.src} srcset={form.config.brand.photo.srcset} sizes="1180px" alt="" class="wide-img" />
      {:else if hero}
        <img src={hero.src} srcset={hero.srcset} sizes="1180px" alt={t('form.welcome.hero_alt')} class="wide-img" />
      {/if}
      <div aria-hidden="true" class="wide-top"></div>
      <div aria-hidden="true" class="wide-bottom"></div>
    </div>
    <div class="wide-grid">
      <h1 data-st class="wide-headline">{t('form.welcome.headline1')}<br />{t('form.welcome.headline2')}</h1>
      <div data-st class="wide-side">
        <p class="wide-tagline">{t('form.welcome.tagline')}</p>
        {@render claimList()}
        <div class="wide-cta">
          <button class="cta" onclick={form.next}>
            {t('form.welcome.cta')}
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
          </button>
        </div>
        {#if resumeLabel}
          <button class="resume wide-resume" onclick={form.resume}>{resumeLabel}</button>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .narrow {
    display: flex;
    flex-direction: column;
  }

  /* Over the backdrop: an empty stage shows the car and the headline, the
     text panel starts where the car fades out. */
  .front {
    position: relative;
    display: flex;
    flex-direction: column;
  }

  .stage {
    position: relative;
    height: 436px;
    flex: none;
  }

  .panel {
    position: relative;
    display: flex;
    flex-direction: column;
    margin: 0 -20px;
    padding: 0 20px 8px;
    /* Where it meets the faded car the panel starts transparent and becomes
       solid as it is scrolled up, so the car disappears behind the text
       instead of showing through it. */
    background: linear-gradient(180deg, rgb(17 18 18 / var(--lift, 0)) 0, var(--bg) 48px);
  }

  .panel::before {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    bottom: 100%;
    height: 110px;
    background: linear-gradient(180deg, rgba(17, 18, 18, 0) 0%, var(--bg) 100%);
    opacity: var(--lift, 0);
    pointer-events: none;
  }

  .tagline {
    position: relative;
    margin: 0 0 10px;
    font: 400 16px/1.5 var(--font-sans);
    color: var(--text-soft);
    text-wrap: pretty;
    max-width: 350px;
  }

  .claims {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 10px;
    font: 500 11px/1.5 var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #8e908b;
  }

  .claim {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .sep {
    width: 3px;
    height: 3px;
    border-radius: 2px;
    background: var(--accent);
  }

  .how {
    list-style: none;
    margin: 18px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
  }

  .how li {
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr);
    align-items: baseline;
    padding: 8px 0;
    border-top: 1px solid #222424;
  }

  .how-n {
    font: 600 22px/1 var(--font-sans);
    letter-spacing: -0.04em;
    color: #3e403f;
  }

  .how-body {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .how-title {
    font: 600 12px/1.3 var(--font-sans);
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text);
  }

  .how-text {
    font: 400 13.5px/1.4 var(--font-sans);
    color: #9c9e99;
  }

  .resume {
    margin-top: 14px;
    align-self: flex-start;
    height: 44px;
    padding: 0;
    border: 0;
    background: transparent;
    font: 500 14.5px/1 var(--font-sans);
    color: var(--accent);
    text-decoration: underline;
    text-underline-offset: 4px;
    cursor: pointer;
  }

  .wide {
    display: flex;
    flex-direction: column;
  }

  .wide-hero {
    position: relative;
    width: 100%;
    aspect-ratio: 2 / 1;
    /* On a laptop screen (1280x800) the 2:1 picture alone would push the
       headline below the fold: the picture gives up height first. */
    max-height: calc(100dvh - 260px);
    min-height: 240px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--bg);
  }

  .wide-img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: 50% 45%;
  }

  .wide-top {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    height: 30%;
    background: linear-gradient(180deg, rgba(17, 18, 18, 0.5) 0%, rgba(17, 18, 18, 0.18) 50%, rgba(17, 18, 18, 0) 100%);
  }

  .wide-bottom {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 32%;
    background: linear-gradient(
      180deg,
      rgba(17, 18, 18, 0) 0%,
      rgba(17, 18, 18, 0.12) 25%,
      rgba(17, 18, 18, 0.4) 50%,
      rgba(17, 18, 18, 0.75) 75%,
      #111212 100%
    );
  }

  .wide-grid {
    position: relative;
    z-index: 1;
    margin-top: -64px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 48px;
    align-items: end;
  }

  .wide-headline {
    margin: 0;
    font-family: var(--font-sans);
    font-weight: 800;
    font-size: clamp(64px, min(8vw, 12.5vh), 112px);
    line-height: 0.88;
    letter-spacing: -0.055em;
    color: var(--text);
  }

  .wide-side {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding-bottom: 6px;
  }

  .wide-tagline {
    margin: 0;
    font: 400 16px/1.5 var(--font-sans);
    color: var(--text-soft);
    text-wrap: pretty;
  }

  .wide-cta {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 6px;
  }

  .cta {
    height: 58px;
    border: 0;
    border-radius: 14px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 17px/1 var(--font-sans);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .cta:hover {
    background: var(--accent-hover);
  }

  .cta:active {
    transform: scale(0.98);
  }

  .wide-resume {
    margin-top: 0;
    height: 40px;
    font-size: 14px;
  }
</style>
