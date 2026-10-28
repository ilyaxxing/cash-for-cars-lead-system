<script lang="ts">
  // Leads: status tabs with counts, search, the card grid and empty states.
  import { getContext } from 'svelte'
  import type { Tab } from './api'
  import LeadCard from './LeadCard.svelte'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const tabs: Tab[] = ['new', 'in_work', 'all']
  let search: HTMLInputElement | undefined = $state()

  const query = $derived(dash.query.trim())
  const tabName = $derived(t(`dashboard.leads.tabs.${dash.tab}`))
  const empty = $derived.by(() => {
    if (!dash.loaded || dash.leads.length) return null
    if (query) {
      const title =
        dash.tab === 'all'
          ? t('dashboard.leads.empty.no_results.title_all', { query })
          : t('dashboard.leads.empty.no_results.title', { tab: tabName, query })
      return { key: 'no_results', title, clear: true, all: dash.tab !== 'all' }
    }
    if (dash.counts.all === 0) return { key: 'none', title: t('dashboard.leads.empty.none.title'), clear: false, all: false }
    return { key: dash.tab, title: t(`dashboard.leads.empty.${dash.tab}.title`), clear: false, all: true }
  })

  function onKey(event: KeyboardEvent) {
    const typing = /INPUT|TEXTAREA/.test(document.activeElement?.tagName ?? '')
    if (event.key === '/' && !typing && dash.openId === null) {
      event.preventDefault()
      search?.focus()
    }
  }

  function onScroll(event: Event) {
    // Older leads load as the list nears its end.
    const main = (event.target as HTMLElement).closest('main')
    if (main && dash.hasMore && main.scrollTop + main.clientHeight > main.scrollHeight - 600) {
      void dash.loadLeads(false)
    }
  }

  $effect(() => {
    const main = search?.closest('main')
    main?.addEventListener('scroll', onScroll, { passive: true })
    return () => main?.removeEventListener('scroll', onScroll)
  })
</script>

<svelte:window onkeydown={onKey} />

<div class="page" style:padding={dash.desk ? '36px 40px 64px' : '20px 16px 32px'}>
  <div class="head">
    <h1 style:font-size={dash.desk ? '40px' : '32px'}>{t('dashboard.leads.title')}</h1>
    <p>{t('dashboard.leads.subtitle')}</p>
  </div>

  {#if dash.pushStatus?.problem}
    <div role="alert" class="warning">
      <span aria-hidden="true" class="warning-badge">!</span>
      <span class="warning-text">
        <span class="warning-title">{t('dashboard.push.warning.title')}</span>
        <span>{t('dashboard.push.warning.text')}</span>
      </span>
      <button class="warning-action" onclick={() => dash.go('settings')}>{t('dashboard.push.warning.action')}</button>
    </div>
  {/if}

  <div class="controls">
    <div role="tablist" aria-label={t('dashboard.leads.tabs_aria')} class="tabs" class:full={!dash.desk}>
      {#each tabs as tab (tab)}
        {@const on = dash.tab === tab}
        <button role="tab" aria-selected={on} class="tab" class:on onclick={() => dash.setTab(tab)}>
          <span>{t(`dashboard.leads.tabs.${tab}`)}</span>
          <span class="n" class:hot={tab === 'new' && dash.counts.new > 0} class:on>{dash.counts[tab]}</span>
        </button>
      {/each}
    </div>
    <label class="search" style:width={dash.desk ? '320px' : '100%'}>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" class="glass">
        <circle cx="7" cy="7" r="4.8" stroke="#A5A7A2" stroke-width="1.5" /><path d="M10.6 10.6L14 14" stroke="#A5A7A2" stroke-width="1.5" stroke-linecap="round" />
      </svg>
      <input
        bind:this={search}
        value={dash.query}
        oninput={(event) => dash.setQuery(event.currentTarget.value)}
        placeholder={t('dashboard.leads.search_placeholder')}
        aria-label={t('dashboard.leads.search_aria')}
        autocomplete="off"
        spellcheck="false"
      />
      {#if query}
        <button class="clear" aria-label={t('dashboard.leads.clear')} onclick={() => { dash.setQuery(''); search?.focus() }}>
          <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 2l6 6M8 2L2 8" stroke="#F4F3EE" stroke-width="1.5" stroke-linecap="round" /></svg>
        </button>
      {:else if dash.desk}
        <span aria-hidden="true" class="kbd">/</span>
      {/if}
    </label>
  </div>

  {#if query && dash.loaded}
    <div class="results">
      {dash.leads.length === 1
        ? t('dashboard.leads.results_one', { tab: tabName })
        : t('dashboard.leads.results', { count: dash.leads.length + (dash.hasMore ? '+' : ''), tab: tabName })}
    </div>
  {/if}

  {#if dash.leads.length}
    <div class="grid">
      {#each dash.leads as lead (lead.id)}
        <LeadCard {lead} />
      {/each}
    </div>
  {:else if empty}
    <div class="empty">
      <span class="empty-tag"><span class="dot"></span>{t(`dashboard.leads.empty.${empty.key}.tag`)}</span>
      <span class="empty-title">{empty.title}</span>
      <span class="empty-text">{t(`dashboard.leads.empty.${empty.key}.text`)}</span>
      <div class="empty-actions">
        {#if empty.clear}<button class="ghost" onclick={() => dash.setQuery('')}>{t('dashboard.leads.clear')}</button>{/if}
        {#if empty.all}<button class="ghost" onclick={() => dash.setTab('all')}>{t('dashboard.leads.view_all')}</button>{/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .page {
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .head {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  h1 {
    margin: 0;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
  }

  p {
    margin: 0;
    font: 400 15px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  /* Not in the design: the warning uses the design's error banner style. */
  .warning {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 14px 16px;
    border-radius: 16px;
    background: rgba(255, 138, 117, 0.08);
    border: 1px solid rgba(255, 138, 117, 0.35);
    animation: ui-in 0.25s both;
  }

  .warning-badge {
    flex: none;
    width: 20px;
    height: 20px;
    border-radius: 10px;
    background: var(--error);
    color: #111212;
    font: 700 12px/20px var(--font-sans);
    text-align: center;
    margin-top: 1px;
  }

  .warning-text {
    flex: 1;
    min-width: 220px;
    display: flex;
    flex-direction: column;
    gap: 3px;
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .warning-title {
    font: 600 15px/1.3 var(--font-sans);
    color: var(--error-soft);
  }

  .warning-action {
    flex: none;
    height: 40px;
    padding: 0 14px;
    border-radius: 10px;
    border: 1px solid rgba(255, 138, 117, 0.4);
    background: transparent;
    color: var(--text);
    font: 500 14px/1 var(--font-sans);
    cursor: pointer;
  }

  .warning-action:hover {
    background: rgba(255, 138, 117, 0.08);
  }

  .controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
  }

  .tabs {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 12px;
    background: var(--surface-sunken);
    border: 1px solid var(--line);
  }

  .tabs.full {
    width: 100%;
  }

  .tab {
    height: 38px;
    padding: 0 12px 0 14px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: var(--text-muted);
    font: 600 14px/1 var(--font-sans);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    cursor: pointer;
    white-space: nowrap;
    transition:
      background-color 0.15s,
      color 0.15s;
  }

  .full .tab {
    flex: 1;
  }

  .tab:hover,
  .tab.on {
    color: var(--text);
  }

  .tab.on {
    background: var(--line);
  }

  .n {
    min-width: 22px;
    height: 20px;
    padding: 0 6px;
    border-radius: 6px;
    background: #222424;
    color: var(--text-soft);
    font: 500 11px/20px var(--font-mono);
    text-align: center;
  }

  .n.on {
    background: #3a3c3c;
  }

  .n.hot {
    background: var(--accent);
    color: var(--on-accent);
  }

  .search {
    position: relative;
    display: flex;
    align-items: center;
    height: 46px;
    padding: 0 6px 0 40px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface);
    transition:
      border-color 0.15s,
      box-shadow 0.15s;
  }

  .search:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgb(var(--accent-rgb) / 0.18);
  }

  .glass {
    position: absolute;
    left: 14px;
    top: 15px;
  }

  .search input {
    flex: 1;
    min-width: 0;
    height: 100%;
    border: 0;
    background: transparent;
    outline: none;
    padding: 0;
    font: 400 15px var(--font-sans);
    color: var(--text);
  }

  .clear {
    flex: none;
    width: 34px;
    height: 34px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .clear:hover {
    background: var(--surface-2);
  }

  .kbd {
    flex: none;
    margin-right: 6px;
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 1px solid var(--line-strong);
    font: 500 11px/20px var(--font-mono);
    color: var(--text-faint);
    text-align: center;
  }

  .results {
    margin-top: -8px;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr));
    gap: 12px;
    align-items: start;
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 36px 28px;
    border-radius: 14px;
    border: 1px dashed #2e3030;
    background: var(--surface-sunken);
    animation: ui-in 0.25s both;
  }

  .empty-tag {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--line-hover);
  }

  .empty-title {
    font: 600 20px/1.2 var(--font-sans);
    letter-spacing: -0.02em;
  }

  .empty-text {
    max-width: 460px;
    font: 400 14.5px/1.5 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .empty-actions {
    display: flex;
    gap: 8px;
    margin-top: 6px;
  }

  .ghost {
    height: 40px;
    padding: 0 14px;
    border-radius: 10px;
    border: 1px solid var(--line-strong);
    background: transparent;
    font: 500 14px/1 var(--font-sans);
    cursor: pointer;
  }

  .ghost:hover {
    background: var(--surface);
  }
</style>
