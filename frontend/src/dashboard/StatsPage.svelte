<script lang="ts">
  // Statistics: totals for a period, purchases, conversion, sources and activity.
  import { getContext } from 'svelte'
  import * as api from './api'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const periods: api.Stats['period'][] = ['7', '30', 'all']

  let period = $state<api.Stats['period']>('30')
  let stats = $state<api.Stats | null>(null)

  $effect(() => {
    const requested = period
    api
      .getStats(requested)
      .then((result) => {
        if (period === requested) stats = result
      })
      .catch((error) => {
        if (error instanceof api.Unauthorized) dash.auth = 'signed_out'
      })
  })

  const w = $derived(dash.width)
  const desk = $derived(dash.desk)
  const pct = (part: number, whole: number) => (whole ? (part / whole) * 100 : 0)

  const sources = $derived.by(() => {
    if (!stats) return []
    const total = stats.total
    const rows = stats.sources.map((source) => {
      const enough = source.leads >= 5
      return {
        ...source,
        share: total ? t('dashboard.stats.share', { pct: Math.round(pct(source.leads, total)) }) : '—',
        width: pct(source.leads, total),
        purchasedWidth: pct(source.purchased, source.leads),
        rate: enough ? source.purchased / source.leads : null,
        conversion: enough ? `${pct(source.purchased, source.leads).toFixed(1)}%` : '—',
        thin: !enough && source.leads > 0,
        best: false,
      }
    })
    const rated = rows.filter((row) => row.rate !== null && row.purchased > 0)
    if (rated.length >= 2) rated.reduce((best, row) => (row.rate! > best.rate! ? row : best)).best = true
    return rows
  })

  const bars = $derived.by(() => {
    if (!stats) return []
    const max = Math.max(1, ...stats.buckets.map((b) => b.leads))
    const thin = !desk && stats.buckets.length > 8
    return stats.buckets.map((bucket, index, all) => {
      const current = index === all.length - 1
      const date = dash.fmt.date(bucket.start)
      const label =
        period === '7'
          ? current
            ? t('dashboard.stats.today')
            : new Intl.DateTimeFormat(dash.present.numberLocale, { weekday: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${bucket.start}T12:00:00Z`))
          : current
            ? t('dashboard.stats.this_week')
            : date
      const tipLabel = period === '7' ? date : t('dashboard.stats.week_of', { date })
      return {
        ...bucket,
        current,
        height: `${Math.round((bucket.leads / max) * 150) + (bucket.leads ? 4 : 2)}px`,
        purchasedHeight: `${pct(bucket.purchased, bucket.leads)}%`,
        label: thin && (all.length - 1 - index) % 2 ? '' : label,
        tip: t('dashboard.stats.bar_tip', { label: tipLabel, leads: bucket.leads, purchased: bucket.purchased }),
      }
    })
  })
</script>

<div class="page" style:padding={desk ? '36px 40px 64px' : '20px 16px 32px'}>
  <div class="head">
    <div class="titles">
      <h1 style:font-size={desk ? '40px' : '32px'}>{t('dashboard.stats.title')}</h1>
      <p>{t('dashboard.stats.subtitle')}</p>
    </div>
    <div role="radiogroup" aria-label={t('dashboard.stats.periods_aria')} class="periods" class:full={!desk}>
      {#each periods as option (option)}
        <button role="radio" aria-checked={period === option} class="period" class:on={period === option} onclick={() => (period = option)}>
          {t(`dashboard.stats.periods.${option}`)}
        </button>
      {/each}
    </div>
  </div>

  {#if stats}
    <div class="metrics" class:compact={!desk} style:grid-template-columns={w >= 1100 ? 'minmax(0,1fr) minmax(0,1fr) minmax(0,1.35fr) minmax(0,1fr)' : 'repeat(2, minmax(0, 1fr))'}>
      <div class="metric">
        <span class="metric-label"><span class="dot"></span>{t('dashboard.stats.total')}</span>
        <span class="metric-body">
          <span class="value" style:font-size={desk ? '44px' : '34px'}>{stats.total}</span>
          <span class="caption">
            {period === 'all'
              ? stats.firstLeadAt
                ? t('dashboard.stats.total_since', { date: dash.fmt.date(stats.firstLeadAt) })
                : t('dashboard.stats.periods.all')
              : t(`dashboard.stats.periods.${period}`)}
          </span>
        </span>
      </div>
      <div class="metric">
        <span class="metric-label"><span class="dot"></span>{t('dashboard.stats.week')}</span>
        <span class="metric-body">
          <span class="value" style:font-size={desk ? '44px' : '34px'}>{stats.week}</span>
          <span class="caption">{t('dashboard.stats.week_since', { date: dash.fmt.date(stats.weekStart) })}</span>
        </span>
      </div>
      <div class="metric bought">
        <span class="metric-label lit"><span class="dot lime"></span>{t('dashboard.stats.bought')}</span>
        <!-- Number and caption side by side on a desk; stacked like the
             other cards on a phone, where the side caption got squeezed. -->
        <span class={desk ? 'metric-row' : 'metric-body'}>
          <span class="value big" style:font-size={desk ? '68px' : '46px'}>{stats.purchased}</span>
          <span class="caption" class:right={desk}>
            {stats.total
              ? stats.total === 1
                ? t('dashboard.stats.bought_from_one')
                : t('dashboard.stats.bought_from', { count: stats.total })
              : t('dashboard.stats.bought_none')}
          </span>
        </span>
      </div>
      <div class="metric">
        <span class="metric-label"><span class="dot"></span>{t('dashboard.stats.conversion')}</span>
        <span class="metric-body">
          <span class="value" style:font-size={desk ? '44px' : '34px'}>{stats.total ? `${pct(stats.purchased, stats.total).toFixed(1)}%` : '—'}</span>
          <span class="caption">
            {stats.total ? t('dashboard.stats.conversion_from', { bought: stats.purchased, total: stats.total }) : t('dashboard.stats.conversion_none')}
          </span>
        </span>
      </div>
    </div>
    <div class="formula">{t('dashboard.stats.formula')}</div>

    <div class="panels" style:grid-template-columns={w >= 1180 ? 'minmax(0,1fr) minmax(0,1.4fr)' : 'minmax(0,1fr)'}>
      <div class="panel sources">
        <div class="panel-head">
          <div class="panel-titles">
            <span class="panel-title">{t('dashboard.stats.sources_title')}</span>
            <span class="panel-text">{t('dashboard.stats.sources_text')}</span>
          </div>
          <div class="legend">
            <span><span class="swatch gray"></span>{t('dashboard.stats.legend_leads')}</span>
            <span><span class="swatch lime"></span>{t('dashboard.stats.legend_purchased')}</span>
          </div>
        </div>
        {#each sources as source (source.source)}
          <div class="source">
            <div class="source-head">
              <span class="source-name">
                <span class="source-label">{source.label}</span>
                {#if source.best}<span class="best">{t('dashboard.stats.best')}</span>{/if}
              </span>
              <span class="source-count"><span class="source-n">{source.leads}</span><span class="share">{source.share}</span></span>
            </div>
            <div role="img" aria-label={t('dashboard.stats.source_aria', { source: source.label, leads: source.leads, purchased: source.purchased })} class="track">
              <div class="fill" style:width="{source.width}%"><div class="fill-lime" style:width="{source.purchasedWidth}%"></div></div>
            </div>
            <div class="source-facts">
              <span>{t('dashboard.stats.purchased')} <span class="bright">{source.purchased}</span></span>
              <span>{t('dashboard.stats.conversion_short')} <span class="bright">{source.conversion}</span></span>
              {#if source.thin}<span>{t('dashboard.stats.thin')}</span>{/if}
            </div>
          </div>
        {/each}
      </div>

      <div class="panel chart">
        <div class="panel-head">
          <div class="panel-titles">
            <span class="panel-title">{period === '7' ? t('dashboard.stats.daily') : t('dashboard.stats.weekly')}</span>
            <span class="panel-text">{period === '7' ? t('dashboard.stats.daily_text') : t('dashboard.stats.weekly_text')}</span>
          </div>
          <div class="legend">
            <span><span class="swatch dim"></span>{t('dashboard.stats.legend_received')}</span>
            <span><span class="swatch lime"></span>{t('dashboard.stats.legend_later')}</span>
          </div>
        </div>
        {#if stats.total}
          <div class="bars-wrap">
            <div class="bars" style:gap={desk ? '8px' : '4px'}>
              {#each bars as bar (bar.start)}
                <div class="bar-col" title={bar.tip}>
                  <span class="bar-n" class:current={bar.current}>{bar.leads || ''}</span>
                  <div class="bar" class:current={bar.current} style:height={bar.height}>
                    <div class="bar-lime" style:height={bar.purchasedHeight}></div>
                  </div>
                </div>
              {/each}
            </div>
            <div class="labels" style:gap={desk ? '8px' : '4px'}>
              {#each bars as bar (bar.start)}
                <span class="bar-label" class:current={bar.current}>{bar.label}</span>
              {/each}
            </div>
          </div>
        {:else}
          <div class="chart-empty">
            <span class="chart-empty-title">{t('dashboard.stats.empty_title')}</span>
            <span class="chart-empty-text">{t('dashboard.stats.empty_text')}</span>
          </div>
        {/if}
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
    gap: 20px;
  }

  .head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .titles {
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
    text-wrap: pretty;
  }

  .periods {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 12px;
    background: var(--surface-sunken);
    border: 1px solid var(--line);
  }

  .periods.full {
    width: 100%;
  }

  .period {
    height: 38px;
    padding: 0 14px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: var(--text-muted);
    font: 600 14px/1 var(--font-sans);
    cursor: pointer;
    white-space: nowrap;
    transition:
      background-color 0.15s,
      color 0.15s;
  }

  .full .period {
    flex: 1;
  }

  .period:hover,
  .period.on {
    color: var(--text);
  }

  .period.on {
    background: var(--line);
  }

  .metrics {
    display: grid;
    gap: 10px;
  }

  .metric {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 20px;
    min-height: 150px;
    padding: 16px 18px;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .metric.bought {
    border-color: #3a3c3c;
  }

  /* On a phone the numbers line up across a row: they follow the label at
     the same distance, whatever the length of the caption under them. */
  .compact .metric {
    justify-content: flex-start;
  }

  .metric-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 11px/1.2 var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  .metric-label.lit {
    color: var(--text);
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--line-hover);
  }

  .dot.lime {
    background: var(--accent);
  }

  .metric-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .metric-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }

  .value {
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    font-variant-numeric: tabular-nums;
  }

  .value.big {
    line-height: 0.9;
    letter-spacing: -0.05em;
    color: var(--accent);
  }

  .caption {
    font: 400 13px/1.35 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .caption.right {
    text-align: right;
  }

  .formula {
    margin-top: -6px;
    font: 400 12.5px/1.5 var(--font-sans);
    color: var(--text-faint);
    text-wrap: pretty;
  }

  .panels {
    display: grid;
    gap: 10px;
    align-items: start;
  }

  .panel {
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .panel.sources {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 18px 18px 8px;
  }

  .panel.chart {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 18px;
  }

  .panel-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: wrap;
  }

  .sources .panel-head {
    margin-bottom: 10px;
  }

  .panel-titles {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .panel-title {
    font: 600 16px/1.2 var(--font-sans);
  }

  .panel-text {
    font: 400 13px/1.4 var(--font-sans);
    color: var(--text-muted);
  }

  .legend {
    display: flex;
    gap: 12px;
    font: 500 11px/1 var(--font-mono);
    color: var(--text-muted);
    padding-top: 3px;
  }

  .legend > span {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .swatch {
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }

  .swatch.gray {
    background: var(--line-hover);
  }

  .swatch.dim {
    background: #4a4c4b;
  }

  .swatch.lime {
    background: var(--accent);
  }

  .source {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 0;
    border-top: 1px solid var(--line-soft);
  }

  .source-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  .source-name {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .source-label {
    font: 600 15px/1.2 var(--font-sans);
  }

  .best {
    height: 20px;
    padding: 0 7px;
    border-radius: 6px;
    border: 1px solid rgb(var(--accent-rgb) / 0.45);
    font: 500 10.5px/18px var(--font-mono);
    color: var(--accent);
  }

  .source-count {
    display: flex;
    align-items: baseline;
    gap: 8px;
    white-space: nowrap;
  }

  .source-n {
    font: 700 20px/1 var(--font-sans);
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
  }

  .share {
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .track {
    height: 8px;
    border-radius: 3px;
    background: var(--surface-2);
    overflow: hidden;
  }

  .fill {
    position: relative;
    height: 100%;
    background: var(--line-hover);
    border-radius: 3px;
    overflow: hidden;
    transition: width 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .fill-lime {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--accent);
    transition: width 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .source-facts {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .bright {
    color: var(--text);
  }

  .bars-wrap {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .bars {
    display: flex;
    align-items: flex-end;
    height: 196px;
    border-bottom: 1px solid #2e3030;
  }

  .bar-col {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 6px;
  }

  .bar-n {
    font: 500 11px/1 var(--font-mono);
    text-align: center;
    color: var(--text-muted);
  }

  .bar-n.current {
    color: var(--text);
  }

  .bar {
    position: relative;
    border-radius: 4px 4px 0 0;
    background: #4a4c4b;
    overflow: hidden;
    transition: height 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .bar.current {
    background: var(--line-hover);
  }

  .bar-lime {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    background: var(--accent);
  }

  .labels {
    display: flex;
  }

  .bar-label {
    flex: 1;
    min-width: 0;
    font: 500 10.5px/1.2 var(--font-mono);
    text-align: center;
    color: var(--text-faint);
    white-space: nowrap;
    overflow: hidden;
  }

  .bar-label.current {
    color: var(--text);
  }

  .chart-empty {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 40px 0;
    align-items: center;
    text-align: center;
  }

  .chart-empty-title {
    font: 600 16px/1.3 var(--font-sans);
  }

  .chart-empty-text {
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-muted);
  }
</style>
