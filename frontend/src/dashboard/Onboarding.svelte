<script lang="ts">
  // One-time setup on a new device. Not in the design; built from the seller
  // form's step layout. Step one puts the dashboard on the home screen (on
  // iPhone, only home-screen apps may receive notifications); step two turns
  // notifications on and sends a test.
  import { getContext, onMount } from 'svelte'
  import BrandMark from '../shared/BrandMark.svelte'
  import type { DashboardState } from './state.svelte'

  interface InstallPrompt extends Event {
    prompt(): Promise<void>
    userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
  }

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t

  const standalone =
    window.matchMedia?.('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  const agent = navigator.userAgent
  const ios = /iPhone|iPad|iPod/.test(agent) || (agent.includes('Mac') && navigator.maxTouchPoints > 1)
  const android = /Android/.test(agent)
  const platform = ios ? 'ios' : android ? 'android' : null
  const steps = platform ? [1, 2, 3].map((n) => t(`dashboard.onboarding.${platform}_steps.${n}`)) : []

  let step = $state<'install' | 'push'>(standalone ? 'push' : 'install')
  let installPrompt = $state<InstallPrompt | null>(null)
  let pushState = $state<'idle' | 'working' | 'done' | 'denied' | 'failed'>('idle')

  // Push is possible here: keys on the server, a browser that can do it, not
  // switched on yet. iPhone Safari outside the home-screen app cannot.
  const canPush = $derived(
    Boolean(dash.pushStatus?.configured) && ['default', 'granted'].includes(dash.pushPermission) && !dash.pushOn,
  )

  onMount(() => {
    const capture = (event: Event) => {
      event.preventDefault()
      installPrompt = event as InstallPrompt
    }
    window.addEventListener('beforeinstallprompt', capture)
    return () => window.removeEventListener('beforeinstallprompt', capture)
  })

  // Nothing left to set up on the push step once the status is known.
  $effect(() => {
    if (step === 'push' && dash.pushStatus && !canPush && pushState === 'idle') dash.finishOnboarding()
  })

  function afterInstall() {
    if (canPush || (!dash.pushStatus && !ios)) step = 'push'
    else dash.finishOnboarding()
  }

  async function install() {
    if (!installPrompt) return
    await installPrompt.prompt()
    await installPrompt.userChoice
    afterInstall()
  }

  async function turnOn() {
    pushState = 'working'
    const result = await dash.enablePush()
    if (result === 'ok') {
      pushState = 'done'
      await dash.testPush()
    } else pushState = result
  }
</script>

<div class="screen">
  <header><BrandMark brand={dash.config.brand} size="medium" /></header>
  <div class="scroll">
    {#key step}
      <div class="content">
        <div class="tag"><span class="dot"></span>{t('dashboard.onboarding.tag')}</div>
        {#if step === 'install'}
          <h1>{t('dashboard.onboarding.install_title')}</h1>
          <p>{t('dashboard.onboarding.install_text')}</p>
          {#if platform}
            <div class="card">
              <span class="card-title">{t(`dashboard.onboarding.${platform}_title`)}</span>
              {#each steps as text, index (index)}
                <div class="step">
                  <span class="n" class:lit={index === 0}>{index + 1}</span>
                  <span class="step-text">{text}</span>
                </div>
              {/each}
            </div>
          {:else}
            <div class="card"><span class="step-text plain">{t('dashboard.onboarding.desktop_text')}</span></div>
          {/if}
        {:else}
          <h1>{t('dashboard.onboarding.push_title')}</h1>
          <p>{t('dashboard.onboarding.push_text')}</p>
          {#if pushState === 'done' || pushState === 'denied' || pushState === 'failed'}
            <div class="card">
              <span class="step-text plain" class:good={pushState === 'done'}>{t(`dashboard.onboarding.push_${pushState}`)}</span>
            </div>
          {/if}
        {/if}
      </div>
    {/key}
  </div>
  <div class="bar">
    {#if step === 'install'}
      {#if installPrompt}
        <button class="primary" onclick={install}>{t('dashboard.onboarding.install_button')}</button>
        <button class="secondary" onclick={afterInstall}>{t('dashboard.onboarding.skip')}</button>
      {:else}
        <button class="primary" onclick={afterInstall}>{t('dashboard.onboarding.continue')}</button>
      {/if}
    {:else if pushState === 'idle' || pushState === 'working'}
      <button class="primary" disabled={pushState === 'working'} onclick={turnOn}>
        {pushState === 'working' ? t('dashboard.onboarding.push_working') : t('dashboard.onboarding.push_button')}
      </button>
      <button class="secondary" onclick={() => dash.finishOnboarding()}>{t('dashboard.onboarding.skip')}</button>
    {:else}
      <button class="primary" onclick={() => dash.finishOnboarding()}>{t('dashboard.onboarding.continue')}</button>
    {/if}
  </div>
</div>

<style>
  .screen {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg);
  }

  header {
    flex: none;
    height: 52px;
    padding: env(safe-area-inset-top) 20px 0;
    display: flex;
    align-items: center;
    box-sizing: content-box;
  }

  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .content {
    max-width: 560px;
    margin: 0 auto;
    padding: 20px 20px 28px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    animation: ui-in 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .tag {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--accent);
  }

  h1 {
    margin: 0;
    font: 700 31px/1.06 var(--font-sans);
    letter-spacing: -0.035em;
    text-wrap: balance;
  }

  p {
    margin: 0 0 16px;
    font: 400 15.5px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .card {
    display: flex;
    flex-direction: column;
    padding: 6px 18px;
    border-radius: 20px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .card-title {
    padding: 12px 0 8px;
    font: 500 11px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .step {
    display: flex;
    gap: 14px;
    padding: 14px 0;
    border-top: 1px solid var(--line-soft);
  }

  .n {
    flex: none;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: var(--surface-2);
    font: 500 11px/24px var(--font-mono);
    text-align: center;
  }

  .n.lit {
    background: var(--accent);
    color: var(--on-accent);
  }

  .step-text {
    font: 400 15px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .step-text.plain {
    padding: 14px 0;
  }

  .step-text.good {
    color: var(--text);
  }

  .bar {
    flex: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px 20px max(18px, env(safe-area-inset-bottom));
    border-top: 1px solid #1f2121;
    max-width: 600px;
    width: 100%;
    margin: 0 auto;
  }

  .primary {
    height: 58px;
    border: 0;
    border-radius: 16px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 17px/1 var(--font-sans);
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .primary:disabled {
    background: var(--accent-pressed);
  }

  .primary:hover:not(:disabled) {
    background: var(--accent-hover);
  }

  .primary:active:not(:disabled) {
    transform: scale(0.98);
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
</style>
