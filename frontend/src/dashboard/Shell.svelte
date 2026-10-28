<script lang="ts">
  // Layout from the design: sidebar on wide screens, header and bottom
  // navigation on phones, the lead panel over the page, toasts and dialogs.
  import { getContext } from 'svelte'
  import BrandMark from '../shared/BrandMark.svelte'
  import ConfirmDialog from './ConfirmDialog.svelte'
  import LeadPanel from './LeadPanel.svelte'
  import LeadsPage from './LeadsPage.svelte'
  import Lightbox from './Lightbox.svelte'
  import NavIcon from './NavIcon.svelte'
  import SettingsPage from './SettingsPage.svelte'
  import type { DashboardState, Screen } from './state.svelte'
  import StatsPage from './StatsPage.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const screens: Screen[] = ['leads', 'stats', 'settings']
  let main: HTMLElement | undefined = $state()

  function go(screen: Screen) {
    dash.go(screen)
    if (main) main.scrollTop = 0
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      if (dash.lightbox !== null) dash.lightbox = null
      else if (dash.confirm) dash.confirm = null
      else if (dash.logoutOpen) dash.logoutOpen = false
      else if (dash.openId !== null) dash.close()
      return
    }
    const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName ?? '')
    if (typing || dash.lightbox !== null) return
    if (dash.openId !== null && (event.key === 'j' || event.key === 'k')) dash.step(event.key === 'j' ? 1 : -1)
  }
</script>

<svelte:window onkeydown={onKey} />

<div class="app" class:desk={dash.desk}>
  {#if dash.desk}
    <aside aria-label={t('dashboard.nav.main')}>
      <div class="brand"><BrandMark brand={dash.config.brand} /></div>
      <div class="badge">{t('dashboard.nav.badge')}</div>
      <nav>
        {#each screens as screen (screen)}
          {@const on = dash.screen === screen}
          <button class="side-item" class:on aria-current={on ? 'page' : 'false'} onclick={() => go(screen)}>
            <NavIcon {screen} {on} />
            <span class="side-label">{t(`dashboard.nav.${screen}`)}</span>
            {#if screen === 'leads' && dash.counts.new > 0}
              <span class="count" aria-label={t('dashboard.nav.new_aria', { count: dash.counts.new })}>{dash.counts.new}</span>
            {/if}
          </button>
        {/each}
      </nav>
      <div class="grow"></div>
      <div class="account">
        <div class="who">
          <span class="initials">{dash.present.upper(dash.config.brand.name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2))}</span>
          <span class="who-text">
            <span class="who-name">{dash.config.brand.name}</span>
            <span class="who-role">{t('dashboard.nav.account')}</span>
          </span>
        </div>
        <button class="side-item logout" onclick={() => (dash.logoutOpen = true)}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.5 3.5H4.5a1 1 0 00-1 1v9a1 1 0 001 1h3M11.5 6l3 3-3 3M14.5 9H7" /></svg>
          {t('dashboard.nav.logout')}
        </button>
      </div>
    </aside>
  {:else}
    <header>
      <div class="header-row"><BrandMark brand={dash.config.brand} size="medium" /></div>
    </header>
  {/if}

  <main bind:this={main}>
    {#if dash.screen === 'leads'}
      <LeadsPage />
    {:else if dash.screen === 'stats'}
      <StatsPage />
    {:else}
      <SettingsPage />
    {/if}
  </main>

  {#if !dash.desk}
    <nav class="bottom" aria-label={t('dashboard.nav.main')}>
      {#each screens as screen (screen)}
        {@const on = dash.screen === screen}
        <button class="bottom-item" class:on aria-current={on ? 'page' : 'false'} onclick={() => go(screen)}>
          <NavIcon {screen} {on} size={20} />
          {t(`dashboard.nav.${screen}`)}
          {#if screen === 'leads' && dash.counts.new > 0}
            <span class="bottom-count" aria-label={t('dashboard.nav.new_aria', { count: dash.counts.new })}>{dash.counts.new}</span>
          {/if}
        </button>
      {/each}
    </nav>
  {/if}

  {#if dash.openId !== null}<LeadPanel />{/if}
  {#if dash.lightbox !== null && dash.detail}<Lightbox />{/if}

  {#if dash.toast}
    <div role="status" class="toast" style:bottom={dash.desk ? '28px' : 'calc(96px + env(safe-area-inset-bottom))'}>
      <span class="toast-dot"></span>{dash.toast.message}
      {#if dash.toast.undo}
        <button class="undo" onclick={dash.toast.undo}>{t('dashboard.toast.undo')}</button>
      {:else}
        <span class="toast-pad"></span>
      {/if}
    </div>
  {/if}

  {#if dash.confirm}
    <ConfirmDialog
      title={t(`dashboard.lead.confirm.${dash.confirm}.title`)}
      text={t(`dashboard.lead.confirm.${dash.confirm}.text`)}
      action={t(`dashboard.lead.confirm.${dash.confirm}.action`)}
      cancel={t('dashboard.lead.cancel')}
      onConfirm={() => dash.applyStatus(dash.confirm!)}
      onCancel={() => (dash.confirm = null)}
    />
  {/if}

  {#if dash.logoutOpen}
    <ConfirmDialog
      title={t('dashboard.logout.title', { brand: dash.config.brand.name })}
      text={t('dashboard.logout.text')}
      action={t('dashboard.logout.confirm')}
      cancel={t('dashboard.logout.cancel')}
      onConfirm={() => dash.signOut()}
      onCancel={() => (dash.logoutOpen = false)}
    />
  {/if}
</div>

<style>
  .app {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    isolation: isolate;
  }

  .app.desk {
    flex-direction: row;
  }

  aside {
    flex: none;
    width: 232px;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg-deep);
    border-right: 1px solid #1f2121;
    padding: 20px 14px 14px;
  }

  .brand {
    display: flex;
    align-items: center;
    height: 40px;
    padding: 0 10px;
  }

  .badge {
    margin: 4px 0 0 42px;
    font: 500 10.5px/1 var(--font-mono);
    letter-spacing: 0.06em;
    color: var(--text-faint);
  }

  nav:not(.bottom) {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: 28px;
  }

  .side-item {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 40px;
    padding: 0 8px 0 10px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    color: var(--text-muted);
    font: 500 14px/1 var(--font-sans);
    cursor: pointer;
    text-align: left;
    transition:
      background-color 0.15s,
      color 0.15s;
  }

  .side-item:hover,
  .side-item.on {
    background: var(--surface);
    color: var(--text);
  }

  .side-label {
    flex: 1;
  }

  .count {
    min-width: 22px;
    height: 20px;
    padding: 0 6px;
    border-radius: 6px;
    background: var(--accent);
    color: var(--on-accent);
    font: 500 11px/20px var(--font-mono);
    text-align: center;
  }

  .grow {
    flex: 1;
  }

  .account {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding-top: 12px;
    border-top: 1px solid #1f2121;
  }

  .who {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 8px;
  }

  .initials {
    flex: none;
    width: 32px;
    height: 32px;
    border-radius: 9px;
    background: var(--surface);
    border: 1px solid var(--line);
    display: flex;
    align-items: center;
    justify-content: center;
    font: 600 12px/1 var(--font-sans);
    letter-spacing: 0.02em;
  }

  .who-text {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .who-name {
    font: 600 13.5px/1.15 var(--font-sans);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .who-role {
    font: 400 12px/1 var(--font-sans);
    color: var(--text-muted);
  }

  .logout {
    padding: 0 10px;
  }

  header {
    flex: none;
    padding: env(safe-area-inset-top) 16px 0;
    background: var(--bg);
    border-bottom: 1px solid #1f2121;
  }

  .header-row {
    height: 52px;
    display: flex;
    align-items: center;
  }

  main {
    position: relative;
    flex: 1;
    min-width: 0;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    background: var(--bg);
  }

  .bottom {
    flex: none;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    padding: 6px 8px max(10px, env(safe-area-inset-bottom));
    background: var(--bg-deep);
    border-top: 1px solid #1f2121;
  }

  .bottom-item {
    position: relative;
    height: 56px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    color: var(--text-muted);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font: 500 11.5px/1 var(--font-sans);
    cursor: pointer;
  }

  .bottom-item.on {
    color: var(--text);
  }

  .bottom-item:active {
    background: var(--surface);
  }

  .bottom-count {
    position: absolute;
    top: 5px;
    left: calc(50% + 6px);
    min-width: 18px;
    height: 16px;
    padding: 0 4px;
    border-radius: 5px;
    background: var(--accent);
    color: var(--on-accent);
    font: 500 10px/16px var(--font-mono);
    text-align: center;
  }

  .toast {
    position: absolute;
    left: 50%;
    z-index: 60;
    display: flex;
    align-items: center;
    gap: 14px;
    height: 48px;
    padding: 0 6px 0 16px;
    border-radius: 12px;
    background: var(--surface-2);
    border: 1px solid #3a3c3c;
    box-shadow: 0 16px 40px -16px rgba(0, 0, 0, 0.7);
    font: 500 14px/1 var(--font-sans);
    white-space: nowrap;
    transform: translateX(-50%);
    animation: ui-toast 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .toast-dot {
    width: 7px;
    height: 7px;
    border-radius: 2px;
    background: var(--accent);
  }

  .undo {
    height: 36px;
    padding: 0 12px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: var(--accent);
    font: 600 14px/1 var(--font-sans);
    cursor: pointer;
  }

  .undo:hover {
    background: #2e3030;
  }

  .toast-pad {
    width: 6px;
  }
</style>
