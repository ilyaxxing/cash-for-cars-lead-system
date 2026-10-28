<script lang="ts">
  // Two big Yes / No tiles, an optional "Don't know" below them, and the
  // follow-up question that opens when the answer unlocks it.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import Check from '../Check.svelte'
  import { optionIds } from '../engine'
  import ErrorText from '../ErrorText.svelte'
  import { pulse, scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field, scroller }: { field: FieldSpec; scroller?: HTMLElement } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const value = $derived(form.answers[field.id])
  const main = $derived(optionIds(field).filter((id) => id !== 'unknown'))
  const follow = $derived(field.follow_up && value === field.follow_up.when ? field.follow_up.fields : [])

  function choose(event: Event, option: string) {
    pulse(event)
    form.set(field.id, option)
    if (option !== field.follow_up?.when) form.autoAdvance()
  }
</script>

<div role="group" aria-label={t(`preset.steps.${form.screen}.title`)} class="grid">
  {#each main as option (option)}
    {@const on = value === option}
    <button data-st class="opt tile" class:on aria-pressed={on} onclick={(event) => choose(event, option)}>
      <span class="tick"><Check {on} size={24} tick={12} stroke={1.6} /></span>
      <span class="word">{t(`preset.yes_no.${option}`)}</span>
    </button>
  {/each}
  {#if field.unknown}
    {@const on = value === 'unknown'}
    <button data-st class="opt unknown" class:on aria-pressed={on} onclick={(event) => choose(event, 'unknown')}>
      <span class="unknown-word">{t('preset.yes_no.unknown')}</span>
      <Check {on} size={24} tick={12} stroke={1.6} />
    </button>
  {/if}
</div>
<ErrorText text={form.errorText(field.id)} gap="12px" />

{#each follow as child (child.id)}
  {@const childValue = form.answers[child.id]}
  <label class="follow">
    <span class="follow-head">
      <span>{form.fieldLabel(child)}</span><span class="optional">{t('form.labels.optional')}</span>
    </span>
    <textarea
      class="field-input"
      value={childValue ?? ''}
      oninput={(event) => form.set(child.id, event.currentTarget.value)}
      onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
      placeholder={t(`preset.fields.${child.id}.placeholder`)}
      rows="3"
      maxlength={child.max_length ?? 400}
    ></textarea>
    <span class="follow-note">{t(`preset.fields.${child.id}.note`)}</span>
    <ErrorText text={form.errorText(child.id)} />
  </label>
{/each}

<style>
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  .tile {
    position: relative;
    height: 112px;
    padding: 16px 18px;
    border-radius: 20px;
    text-align: left;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .tile:active,
  .unknown:active {
    transform: scale(0.97);
  }

  .tick {
    align-self: flex-end;
  }

  .word {
    font: 700 28px/1 var(--font-sans);
    letter-spacing: -0.03em;
  }

  /* Not in the design: the third answer, in the same visual language. */
  .unknown {
    grid-column: span 2;
    height: 64px;
    padding: 0 18px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    text-align: left;
  }

  .unknown-word {
    font: 600 17px/1 var(--font-sans);
    letter-spacing: -0.01em;
  }

  .follow {
    margin-top: 14px;
    padding: 18px;
    border-radius: 20px;
    background: var(--surface);
    border: 1px solid var(--line);
    display: flex;
    flex-direction: column;
    gap: 10px;
    animation: ui-in 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .follow-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font: 500 14.5px/1.3 var(--font-sans);
  }

  .optional {
    color: var(--text-muted);
    font-weight: 400;
  }

  textarea {
    padding: 14px 16px;
    border-radius: 14px;
    background: var(--bg) !important;
    font: 400 16.5px/1.45 var(--font-sans);
    resize: none;
  }

  .follow-note {
    font: 400 13px/1.4 var(--font-sans);
    color: var(--text-muted);
  }
</style>
