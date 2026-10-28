<script lang="ts">
  // A small set of options in a two-column grid (preferred contact method).
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import Check from '../Check.svelte'
  import ErrorText from '../ErrorText.svelte'
  import { pulse } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field }: { field: FieldSpec } = $props()
  const form = getContext<FormState>('form')
  const t = form.t
  const selected = $derived(form.answers[field.id] ?? field.default)
</script>

<div data-st class="stack">
  <span class="label">{form.fieldLabel(field)}</span>
  <div role="group" aria-label={form.fieldLabel(field)} class="grid">
    {#each field.options as option (option.id)}
      {@const on = selected === option.id}
      <button
        class="opt choice"
        class:on
        aria-pressed={on}
        disabled={form.busy}
        onclick={(event) => {
          pulse(event)
          form.set(field.id, option.id)
        }}
      >
        <span>{t(`preset.options.${field.id}.${option.id}.label`)}</span>
        <Check {on} />
      </button>
    {/each}
  </div>
  <ErrorText text={form.errorText(field.id)} />
</div>

<style>
  .stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .choice {
    height: 52px;
    padding: 0 14px;
    border-radius: 14px;
    font: 600 15px/1 var(--font-sans);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .choice:active {
    transform: scale(0.96);
  }
</style>
