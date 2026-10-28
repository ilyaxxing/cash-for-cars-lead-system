<script lang="ts">
  // Popular answers as chips (models of the chosen make) plus a text field.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import { suggestionsFor } from '../engine'
  import ErrorText from '../ErrorText.svelte'
  import { pulse, scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field, scroller, free = false }: { field: FieldSpec; scroller?: HTMLElement; free?: boolean } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const options = $derived(free ? [] : suggestionsFor(field, form.answers))
  const value = $derived(form.answers[field.id])
  const parent = $derived(field.suggestions_by ? form.answers[field.suggestions_by] : undefined)
  const heading = $derived(
    free || !parent
      ? form.fieldLabel(field)
      : t(`preset.fields.${field.id}.label_for_make`, { make: String(parent) }),
  )
  const error = $derived(form.errorText(field.id))
</script>

<div class="label head">{heading}</div>
{#if options.length}
  <div role="group" aria-label={t('form.labels.popular_models')} class="chips">
    {#each options as option (option)}
      {@const on = value === option}
      <button
        class="opt chip"
        class:on
        aria-pressed={on}
        onclick={(event) => {
          pulse(event)
          form.set(field.id, option)
          form.autoAdvance()
        }}>{option}</button
      >
    {/each}
  </div>
{/if}
<label class="stack">
  <span class="visually-hidden">{form.fieldLabel(field)}</span>
  <input
    class="field-input text"
    class:invalid={error}
    value={value ?? ''}
    oninput={(event) => form.set(field.id, event.currentTarget.value)}
    onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
    onkeydown={(event) => event.key === 'Enter' && (event.preventDefault(), form.next())}
    placeholder={options.length
      ? t(`preset.fields.${field.id}.placeholder`)
      : t(`preset.fields.${field.id}.placeholder_free`)}
    autocomplete="off"
    aria-invalid={Boolean(error)}
  />
  <ErrorText text={error} />
</label>

<style>
  .head {
    font: 500 13.5px/1 var(--font-sans);
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    height: 46px;
    padding: 0 16px;
    border-radius: 12px;
    font: 600 14.5px/1 var(--font-sans);
    animation: ui-chip 0.25s both;
  }

  .chip:active {
    transform: scale(0.95);
  }

  .stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .text {
    height: 56px;
    padding: 0 16px;
    border-radius: 14px;
    font: 400 17px var(--font-sans);
  }
</style>
