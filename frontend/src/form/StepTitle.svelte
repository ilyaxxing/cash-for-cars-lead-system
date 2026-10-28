<script lang="ts">
  // "03 / Details" tag, the question, and its hint.
  import { getContext } from 'svelte'
  import type { FormState } from './state.svelte'

  let { tag, title, hint }: { tag: string; title: string; hint: string } = $props()
  const form = getContext<FormState>('form')
  const number = $derived(String(form.progress.n).padStart(2, '0'))
  // Hints are optional in the locale: an unresolved key means "no hint".
  const hasHint = $derived(Boolean(hint) && !hint.startsWith('preset.') && !hint.startsWith('form.'))
</script>

<div class="block">
  <div data-st class="tag"><span class="dot"></span>{number} / {tag}</div>
  <h1 data-st style:font-size={form.wide ? '42px' : '31px'}>{title}</h1>
  {#if hasHint}<p data-st>{hint}</p>{/if}
</div>

<style>
  .block {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 26px;
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
    font-weight: 700;
    line-height: 1.06;
    letter-spacing: -0.035em;
    text-wrap: balance;
  }

  p {
    margin: 0;
    font: 400 15.5px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }
</style>
