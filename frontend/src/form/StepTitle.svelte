<script lang="ts">
  // The step's name, the question, and its hint.
  import { getContext } from 'svelte'
  import type { FormState } from './state.svelte'

  let { tag, title, hint }: { tag: string; title: string; hint: string } = $props()
  const form = getContext<FormState>('form')
  // Hints are optional in the locale: an unresolved key means "no hint".
  const hasHint = $derived(Boolean(hint) && !hint.startsWith('preset.') && !hint.startsWith('form.'))
</script>

<div class="block">
  <div data-st class="tag">{tag}</div>
  <h1 data-st style:font-size={form.wide ? '56px' : '40px'}>{title}</h1>
  {#if hasHint}<p data-st>{hint}</p>{/if}
</div>

<style>
  .block {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 20px;
  }

  .tag {
    font: 700 15px/1 var(--font-display);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  h1 {
    margin: 0;
    font-family: var(--font-display);
    font-weight: 800;
    line-height: 0.94;
    letter-spacing: 0.004em;
    text-transform: uppercase;
    text-wrap: balance;
  }

  p {
    margin: 0;
    font: 400 15.5px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }
</style>
