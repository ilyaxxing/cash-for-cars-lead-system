<script lang="ts">
  // A lead in the list: the first photo, status, time, car, price and two
  // facts. The other photos are in the opened lead.
  import { getContext } from 'svelte'
  import type { Card } from './api'
  import { summarize } from './car'
  import type { DashboardState } from './state.svelte'

  let { lead }: { lead: Card } = $props()
  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t

  const car = $derived(summarize(dash.present, lead))
  const rejected = $derived(lead.status === 'rejected')
</script>

<button
  class="card status-{lead.status}"
  class:new={lead.status === 'new'}
  class:rejected
  aria-label={t('dashboard.leads.card_aria', { car: car.title, year: String(lead.answers.year ?? ''), status: dash.statusLabel(lead.status) })}
  onclick={() => dash.open(lead.id)}
>
  {#if lead.photoCount && lead.photos[0]}
    <span class="photos">
      <span class="main">
        <img src={lead.photos[0].thumbUrl} alt="" loading="lazy" />
        {#if lead.photoCount > 1}
          <span class="count">{t('dashboard.leads.photo_count', { count: lead.photoCount })}</span>
        {/if}
      </span>
    </span>
  {/if}
  <span class="body">
    <span class="meta">
      <span class="status"><span class="status-dot"></span>{dash.statusLabel(lead.status)}</span>
      <span class="when">{dash.fmt.when(lead.createdAt)}</span>
    </span>
    <span class="heading">
      <span class="title">{car.title}</span>
      {#if car.price}<span class="price">{car.price}</span>{/if}
    </span>
    <span class="sub">{car.sub}</span>
    <span class="rows">
      {#if car.conditionField}
        <span class="row"><span class="key">{dash.present.fieldLabel(car.conditionField)}</span><span class="value">{car.condition}</span></span>
      {/if}
      {#if car.vinField}
        <span class="row">
          <span class="key">{dash.present.fieldLabel(car.vinField)}</span>
          <span class="value" class:mono={car.vin} class:missing={!car.vin}>{car.vin || t('dashboard.lead.not_provided')}</span>
        </span>
      {/if}
    </span>
  </span>
</button>

<style>
  .card {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
    padding: 0;
    text-align: left;
    border-radius: 22px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
    overflow: hidden;
    transition:
      border-color 0.15s,
      transform 0.12s;
    animation: ui-in 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .card.new {
    border-color: #3a3c3c;
  }

  .card.rejected {
    background: var(--surface-sunken);
  }

  .card:hover {
    border-color: var(--line-hover);
  }

  .card:active {
    transform: scale(0.99);
  }

  .photos {
    display: block;
    padding: 3px 3px 0;
  }

  .main {
    position: relative;
    display: block;
    aspect-ratio: 16 / 10;
    overflow: hidden;
    border-radius: 17px;
    background: var(--surface-2);
  }

  /* How many photos wait inside the lead. */
  .count {
    position: absolute;
    right: 10px;
    bottom: 10px;
    padding: 5px 8px;
    border-radius: 8px;
    background: rgba(17, 18, 18, 0.78);
    font: 500 11px/1 var(--font-mono);
    color: var(--text);
  }

  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .body {
    display: flex;
    flex-direction: column;
    padding: 18px 22px 8px;
  }

  .meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 14px;
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font: 500 11.5px/1 var(--font-mono);
    color: var(--status-c);
  }

  .when {
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-muted);
    white-space: nowrap;
  }

  .heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
  }

  .title {
    font: 700 26px/1.1 var(--font-sans);
    letter-spacing: -0.03em;
    text-wrap: balance;
    min-width: 0;
  }

  .price {
    flex: none;
    font: 700 22px/1.25 var(--font-sans);
    letter-spacing: -0.025em;
    font-variant-numeric: tabular-nums;
  }

  .rejected .title,
  .rejected .price {
    color: var(--text-muted);
  }

  .sub {
    margin-top: 7px;
    font: 500 15px/1.3 var(--font-sans);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  .rows {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
  }

  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    padding: 12px 0;
    border-top: 1px solid var(--line-soft);
  }

  .key {
    flex: none;
    font: 400 13.5px/1.3 var(--font-sans);
    color: var(--text-muted);
  }

  .value {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font: 500 14.5px/1.3 var(--font-sans);
    letter-spacing: 0.02em;
    text-align: right;
  }

  .value.mono {
    font: 500 13.5px/1.3 var(--font-mono);
  }

  .value.missing {
    color: var(--text-faint);
  }
</style>
