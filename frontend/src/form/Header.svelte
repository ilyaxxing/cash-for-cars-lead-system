<script lang="ts">
  // Back button, small brand mark, step counter and the segmented progress bar.
  import { getContext } from 'svelte'
  import BrandMark from '../shared/BrandMark.svelte'
  import type { FormState } from './state.svelte'

  let { pad, maxWidth }: { pad: string; maxWidth: string } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const pad2 = (n: number) => String(n).padStart(2, '0')
  const p = $derived(form.progress)
  const label = $derived(t('form.header.step', { n: p.n, total: p.total }))
  const remaining = $derived(
    p.last
      ? t('form.header.last_step')
      : p.remainingSeconds < 60
        ? t('form.header.under_a_minute')
        : t('form.header.minutes_left', { minutes: Math.round(p.remainingSeconds / 60) }),
  )
</script>

<div class="header" style:padding={pad}>
  <div class="inner" style:max-width={maxWidth}>
    <div class="row">
      <button class="back" onclick={form.back} aria-label={t('form.header.back')} disabled={form.busy}>
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path
            d="M12.5 4.5L7 10l5.5 5.5"
            stroke="#F4F3EE"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <BrandMark brand={form.config.brand} size="small" />
      <div class="count">{pad2(p.n)}/{pad2(p.total)}</div>
    </div>
    <div role="progressbar" aria-label={label} aria-valuemin="2" aria-valuemax={p.total} aria-valuenow={p.n} class="segments">
      {#each p.segments as fill, index (index)}
        <div class="segment"><div class="fill" style:width="{fill * 100}%"></div></div>
      {/each}
    </div>
    <div class="labels"><span>{label}</span><span>{remaining}</span></div>
  </div>
</div>

<style>
  .header {
    flex: none;
  }

  .inner {
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 44px;
  }

  .back {
    width: 44px;
    height: 44px;
    margin-left: -12px;
    border: 0;
    background: transparent;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.12s;
  }

  .back:hover {
    background: var(--surface);
  }

  .back:active {
    transform: scale(0.92);
  }

  .count {
    width: 44px;
    margin-right: -12px;
    text-align: right;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .segments {
    display: flex;
    gap: 4px;
  }

  .segment {
    flex: 1;
    height: 3px;
    border-radius: 2px;
    background: var(--line);
    overflow: hidden;
  }

  .fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .labels {
    display: flex;
    justify-content: space-between;
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-muted);
  }
</style>
