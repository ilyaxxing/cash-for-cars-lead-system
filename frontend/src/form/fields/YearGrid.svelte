<script lang="ts">
  // Year as a grid of buttons: recent years first, older ones on request,
  // and one "Earlier" answer for everything before the grid.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import { EARLIER, yearOptions } from '../engine'
  import ErrorText from '../ErrorText.svelte'
  import { pulse } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field, onPicked }: { field: FieldSpec; onPicked?: () => void } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const options = $derived(yearOptions(field, new Date()))
  const value = $derived(form.answers[field.id])
  const older = $derived(
    form.showOlderYears || value === EARLIER || (typeof value === 'number' && options.older.includes(value)),
  )
  const years = $derived<(number | string)[]>([
    ...options.recent,
    ...(older ? [...options.older, ...(field.earlier !== undefined ? [EARLIER] : [])] : []),
  ])
</script>

<div class="label head">{form.fieldLabel(field)}</div>
<div role="group" aria-label={form.fieldLabel(field)} class="grid">
  {#each years as year (year)}
    {@const on = value === year}
    <button
      data-st
      class="opt year"
      class:on
      aria-pressed={on}
      onclick={(event) => {
        pulse(event)
        form.set(field.id, year)
        onPicked?.()
      }}>{year === EARLIER ? t(`preset.fields.${field.id}.earlier`) : year}</button
    >
  {/each}
</div>
<button class="toggle" onclick={() => (form.showOlderYears = !older)}>
  {older ? t(`preset.fields.${field.id}.show_fewer`) : t(`preset.fields.${field.id}.show_older`)}
</button>
<div class="error"><ErrorText text={form.errorText(field.id)} /></div>

<style>
  .head {
    font: 500 13.5px/1 var(--font-sans);
    margin-bottom: 10px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
  }

  .year {
    height: 46px;
    border-radius: 12px;
    font: 500 15px/1 var(--font-mono);
  }

  .year.on {
    color: var(--accent);
  }

  .year:active {
    transform: scale(0.94);
  }

  .toggle {
    margin-top: 6px;
    height: 44px;
    padding: 0;
    border: 0;
    background: transparent;
    font: 500 14px/1 var(--font-sans);
    color: var(--text);
    text-decoration: underline;
    text-underline-offset: 4px;
    text-decoration-color: var(--text-faint);
    cursor: pointer;
  }

  .error :global(.error) {
    margin: 4px 0;
  }
</style>
