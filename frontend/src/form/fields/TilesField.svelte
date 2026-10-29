<script lang="ts">
  // Quick-pick tiles (the make), with "Other" opening a free-text field.
  // Fields that depend on this one (the model) appear below once it is set.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import Check from '../Check.svelte'
  import ErrorText from '../ErrorText.svelte'
  import { pulse, reveal, scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'
  import ChipsField from './ChipsField.svelte'

  let { field, dependents, scroller }: { field: FieldSpec; dependents: FieldSpec[]; scroller?: HTMLElement } =
    $props()
  const form = getContext<FormState>('form')
  const t = form.t
  const OTHER = '__other__'

  let section: HTMLDivElement | undefined = $state()
  const tiles = $derived([...(field.suggestions as string[]), ...(field.other ? [OTHER] : [])])
  const value = $derived(form.answers[field.id])
  const open = $derived(form.otherMake || (typeof value === 'string' && value !== ''))
  const error = $derived(form.errors[field.id])

  function choose(event: Event, tile: string) {
    pulse(event)
    const other = tile === OTHER
    const changed = other ? !form.otherMake : form.otherMake || value !== tile
    if (changed) {
      // A different make: the typed make and the model no longer apply.
      form.otherMake = other
      form.set(field.id, other ? '' : tile)
      for (const dependent of dependents) form.set(dependent.id, undefined)
    }
    // On phones, bring the model question into view once the make is picked,
    // moving only as far as needed.
    if (!form.wide && scroller) setTimeout(() => section && reveal(section, scroller), 60)
  }
</script>

<div class="label head">{form.fieldLabel(field)}</div>
<div role="group" aria-label={form.fieldLabel(field)} class="grid">
  {#each tiles as tile (tile)}
    {@const on = tile === OTHER ? form.otherMake : !form.otherMake && value === tile}
    <button
      data-st
      class="opt tile"
      class:on
      class:wide-tile={tile === OTHER}
      aria-pressed={on}
      onclick={(event) => choose(event, tile)}
    >
      <span class="name" class:long={tile !== OTHER && tile.length > 9}>{tile === OTHER ? t('form.labels.other') : tile}</span>
      <span class="tick"><Check {on} /></span>
    </button>
  {/each}
</div>
{#if error && error.code !== 'other_required'}
  <ErrorText text={form.errorText(field.id)} gap="12px" />
{/if}

{#if open}
  <div class="reveal" bind:this={section}>
    {#if form.otherMake}
      <label class="stack">
        <span class="label">{t(`preset.fields.${field.id}.other_label`)}</span>
        <input
          class="field-input text"
          class:invalid={error}
          value={value ?? ''}
          oninput={(event) => form.set(field.id, event.currentTarget.value)}
          onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
          onkeydown={(event) => event.key === 'Enter' && (event.preventDefault(), form.next())}
          placeholder={t(`preset.fields.${field.id}.other_placeholder`)}
          autocomplete="off"
          aria-invalid={Boolean(error)}
        />
        {#if error?.code === 'other_required'}<ErrorText text={form.errorText(field.id)} />{/if}
      </label>
    {/if}
    {#each dependents as dependent (dependent.id)}
      <ChipsField field={dependent} {scroller} free={form.otherMake} />
    {/each}
  </div>
{/if}

<style>
  .head {
    font: 500 13.5px/1 var(--font-sans);
    margin-bottom: 10px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .tile {
    position: relative;
    height: 64px;
    padding: 0 12px 11px;
    border-radius: 14px;
    font: 600 14px/1.15 var(--font-sans);
    display: flex;
    align-items: flex-end;
    text-align: left;
  }

  .tile:active {
    transform: scale(0.96);
  }

  .wide-tile {
    grid-column: span 2;
  }

  .name {
    min-width: 0;
    overflow-wrap: anywhere;
  }

  /* A long make (Volkswagen) fits a third of a phone without breaking. */
  .name.long {
    font-size: 12.5px;
    letter-spacing: -0.01em;
  }

  .tick {
    position: absolute;
    top: 9px;
    right: 9px;
  }

  .reveal {
    margin-top: 26px;
    padding-top: 22px;
    border-top: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    gap: 14px;
    animation: ui-in 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both;
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
