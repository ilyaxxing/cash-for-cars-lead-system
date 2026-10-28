<script lang="ts">
  // Settings → Notifications, as in the design: switch, browser permission,
  // test notification.
  import { getContext } from 'svelte'
  import type { DashboardState } from './state.svelte'

  let { columns }: { columns: string } = $props()
  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const brand = dash.config.brand.name

  let asking = $state(false)
  let nudge = $state(false)
  let test = $state<'idle' | 'loading' | 'ok' | 'error'>('idle')
  let testError = $state('')

  const configured = $derived(dash.pushStatus?.configured ?? true)
  const blocked = $derived(['denied', 'unsupported', 'ios_home', 'insecure'].includes(dash.pushPermission) || !configured)
  const permissionKey = $derived(asking ? 'asking' : !configured ? 'not_configured' : dash.pushPermission)

  async function toggle() {
    test = 'idle'
    if (dash.pushOn) {
      await dash.disablePush()
      return
    }
    if (blocked) {
      nudge = true
      return
    }
    asking = true
    nudge = false
    const result = await dash.enablePush()
    asking = false
    if (result !== 'ok') nudge = true
  }

  async function sendTest() {
    if (!dash.pushOn || test === 'loading') return
    test = 'loading'
    const result = await dash.testPush()
    if (result === 'ok') test = 'ok'
    else {
      test = 'error'
      testError =
        result === 'permission' ? t('dashboard.push.test_fail_permission') : t('dashboard.push.test_fail', { brand })
    }
  }

  const label = $derived(
    test === 'loading'
      ? t('dashboard.push.test_sending')
      : test === 'ok'
        ? t('dashboard.push.test_again')
        : test === 'error'
          ? t('dashboard.push.test_retry')
          : t('dashboard.push.test_send'),
  )
</script>

<section style:grid-template-columns={columns}>
  <div class="about">
    <h2>{t('dashboard.push.section_title')}</h2>
    <span>{t('dashboard.push.section_text', { brand })}</span>
  </div>
  <div class="card">
    <div class="top">
      <div class="pair">
        <span id="push-title" class="name">{t('dashboard.push.title')}</span>
        <span class="desc">{t('dashboard.push.text')}</span>
      </div>
      <button role="switch" aria-checked={dash.pushOn} aria-labelledby="push-title" class="switch" class:on={dash.pushOn} disabled={asking} onclick={toggle}>
        <span class="knob"></span>
      </button>
    </div>
    <div class="permission" class:nudged={nudge && blocked}>
      {#if asking}
        <span aria-hidden="true" class="spinner small"></span>
      {:else}
        <span aria-hidden="true" class="perm-dot" class:ok={dash.pushPermission === 'granted' && configured} class:bad={blocked}></span>
      {/if}
      <span role="status" class="perm-text">
        <span class="perm-title">{t(`dashboard.push.permission.${permissionKey}.title`)}</span>
        <span class="perm-desc">{t(`dashboard.push.permission.${permissionKey}.text`, { brand })}</span>
      </span>
    </div>
    <div class="test">
      <div class="pair grow">
        <span class="item">{t('dashboard.push.test_title')}</span>
        <span class="desc small">{dash.pushOn ? t('dashboard.push.test_hint_on') : t('dashboard.push.test_hint_off')}</span>
      </div>
      <button class="test-button" class:off={!dash.pushOn} disabled={!dash.pushOn || test === 'loading'} aria-busy={test === 'loading'} onclick={sendTest}>
        {#if test === 'loading'}<span aria-hidden="true" class="spinner"></span>{/if}
        {label}
      </button>
    </div>
    {#if test === 'ok'}
      <div role="status" class="ok">
        <span aria-hidden="true" class="ok-mark"><svg width="10" height="10" viewBox="0 0 10 10"><path d="M2 5.2l2 2L8 3" style="stroke: var(--on-accent)" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round" /></svg></span>
        <span>{t('dashboard.push.test_ok')}</span>
      </div>
    {:else if test === 'error'}
      <div role="alert" class="fail">
        <span aria-hidden="true" class="badge">!</span>
        <span class="fail-text"><span class="fail-title">{t('dashboard.push.test_fail_title')}</span><span>{testError}</span></span>
      </div>
    {/if}
  </div>
</section>

<style>
  section {
    display: grid;
    gap: 14px 32px;
    padding-top: 24px;
    border-top: 1px solid #222424;
  }

  .about {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  h2 {
    margin: 0;
    font: 600 15.5px/1.2 var(--font-sans);
  }

  .about span {
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .card {
    display: flex;
    flex-direction: column;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
    padding: 18px;
  }

  .pair {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .grow {
    flex: 1;
    min-width: 200px;
    gap: 4px;
  }

  .name {
    font: 600 15.5px/1.25 var(--font-sans);
  }

  .item {
    font: 500 14.5px/1.3 var(--font-sans);
  }

  .desc {
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .desc.small {
    font-size: 13px;
  }

  .switch {
    flex: none;
    position: relative;
    width: 50px;
    height: 30px;
    margin-top: 2px;
    padding: 0;
    border-radius: 15px;
    border: 1.5px solid #4a4c4b;
    background: var(--surface-2);
    cursor: pointer;
    transition:
      background-color 0.2s,
      border-color 0.2s;
  }

  .switch:hover {
    border-color: var(--text-faint);
  }

  .switch.on {
    background: var(--accent);
    border-color: var(--accent);
  }

  .knob {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 21px;
    height: 21px;
    border-radius: 11px;
    background: var(--text-muted);
    transition:
      transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1),
      background-color 0.2s;
  }

  .on .knob {
    background: var(--on-accent);
    transform: translateX(20px);
  }

  .permission {
    margin: 0 18px 18px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--surface-sunken);
    border: 1px solid var(--line);
    transition: border-color 0.2s;
  }

  .permission.nudged {
    border-color: rgba(255, 138, 117, 0.45);
  }

  .perm-dot {
    flex: none;
    margin-top: 5px;
    width: 7px;
    height: 7px;
    border-radius: 2px;
    background: var(--text-muted);
  }

  .perm-dot.ok {
    background: var(--accent);
  }

  .perm-dot.bad {
    background: var(--error);
  }

  .perm-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .perm-title {
    font: 500 13.5px/1.35 var(--font-sans);
  }

  .perm-desc {
    font: 400 13px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .test {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    padding: 16px 18px;
    border-top: 1px solid var(--line-soft);
  }

  .test-button {
    flex: none;
    height: 44px;
    padding: 0 16px;
    border-radius: 12px;
    border: 1px solid var(--line-strong);
    background: var(--surface-2);
    color: var(--text);
    font: 600 14.5px/1 var(--font-sans);
    display: flex;
    align-items: center;
    gap: 9px;
    cursor: pointer;
    transition:
      background-color 0.15s,
      border-color 0.15s,
      transform 0.12s;
  }

  .test-button.off {
    opacity: 0.45;
  }

  .test-button:hover:not(:disabled) {
    border-color: var(--line-hover);
  }

  .test-button:active:not(:disabled) {
    transform: scale(0.97);
  }

  .spinner {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid rgba(244, 243, 238, 0.25);
    border-top-color: var(--text);
    animation: ui-spin 0.7s linear infinite;
  }

  .spinner.small {
    flex: none;
    margin-top: 2px;
    width: 14px;
    height: 14px;
    border-color: var(--line-strong);
    border-top-color: var(--text);
  }

  .ok {
    margin: 0 18px 18px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgb(var(--accent-rgb) / 0.06);
    border: 1px solid rgb(var(--accent-rgb) / 0.3);
    font: 400 13.5px/1.45 var(--font-sans);
    color: #e4e3dd;
    animation: ui-in 0.25s both;
  }

  .ok-mark {
    flex: none;
    width: 18px;
    height: 18px;
    border-radius: 9px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .fail {
    margin: 0 18px 18px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255, 138, 117, 0.08);
    border: 1px solid rgba(255, 138, 117, 0.35);
    animation: ui-in 0.25s both;
  }

  .badge {
    flex: none;
    width: 18px;
    height: 18px;
    border-radius: 9px;
    background: var(--error);
    color: #111212;
    font: 700 11px/18px var(--font-sans);
    text-align: center;
  }

  .fail-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-soft);
    text-wrap: pretty;
  }

  .fail-title {
    font: 600 14px/1.3 var(--font-sans);
    color: var(--error-soft);
  }
</style>
