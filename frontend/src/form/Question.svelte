<script lang="ts">
  // One questionnaire step, built from the preset: title block, the fields
  // drawn by type and widget, and the step's note.
  import { getContext, tick } from 'svelte'
  import type { FieldSpec, Step } from '../shared/config'
  import ChipsField from './fields/ChipsField.svelte'
  import ChoiceGrid from './fields/ChoiceGrid.svelte'
  import Consent from './fields/Consent.svelte'
  import LevelSelect from './fields/LevelSelect.svelte'
  import NumberField from './fields/NumberField.svelte'
  import TextField from './fields/TextField.svelte'
  import TilesField from './fields/TilesField.svelte'
  import VinField from './fields/VinField.svelte'
  import YearGrid from './fields/YearGrid.svelte'
  import YesNoField from './fields/YesNoField.svelte'
  import { scrollIntoView } from './motion'
  import type { FormState } from './state.svelte'
  import StepTitle from './StepTitle.svelte'

  let { step, scroller }: { step: Step; scroller?: HTMLElement } = $props()
  const form = getContext<FormState>('form')
  const t = form.t
  let container: HTMLDivElement | undefined = $state()

  const car = $derived(
    [form.answers.make, form.answers.model].filter((part) => typeof part === 'string' && part).join(' '),
  )

  // Fields that hang off a tiles field (model under make) render inside it.
  const isDependent = (field: FieldSpec) =>
    Boolean(field.suggestions_by && step.fields.some((f) => f.id === field.suggestions_by && f.widget === 'tiles'))
  const dependentsOf = (field: FieldSpec) => step.fields.filter((f) => f.suggestions_by === field.id)
  const shown = $derived(step.fields.filter((field) => !isDependent(field)))

  // Two short text fields share a row (city and ZIP code).
  const sideBySide = $derived(
    shown.length === 2 && shown.every((f) => f.type === 'text' && !f.widget && !f.multiline && f.format !== 'vin'),
  )

  function marker(field: FieldSpec): string {
    if (!step.submit) return ''
    if (field.required) return t('form.labels.required')
    const conditional = Object.entries(field.required_when ?? {}).some(([other, value]) => {
      const fieldOther = form.findField(other)
      return (form.answers[other] ?? fieldOther?.default) === value
    })
    return conditional ? t('form.labels.required_for_email') : t('form.labels.optional')
  }

  // The keyboard's own key moves on. On iPhone the open keyboard covers the
  // Continue button, so its key reads Next (to the next field of the step)
  // or Go (on the last one, where the field's own Enter handler continues).
  function typingFields(): HTMLInputElement[] {
    if (!container) return []
    return [...container.querySelectorAll<HTMLInputElement>('input')].filter(
      (input) => !['checkbox', 'radio', 'hidden', 'file'].includes(input.type) && !input.classList.contains('trap') && !input.disabled,
    )
  }

  function labelEnterKey() {
    const fields = typingFields()
    fields.forEach((field, i) => (field.enterKeyHint = i < fields.length - 1 ? 'next' : 'go'))
  }

  // Fields come and go with the answers (a follow-up question): label them
  // after every render, and again on focus.
  $effect(() => {
    void form.answers
    void shown
    tick().then(labelEnterKey)
  })

  function enterToNextField(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.isComposing) return
    const fields = typingFields()
    const target = event.target
    if (!(target instanceof HTMLInputElement)) return
    const next = fields[fields.indexOf(target) + 1]
    if (!next || !fields.includes(target)) return
    event.preventDefault()
    event.stopPropagation()
    next.focus()
  }

  function focusNextNumber(after: FieldSpec) {
    const index = shown.indexOf(after)
    const next = shown[index + 1]
    if (next?.type === 'number' && form.answers[next.id] === undefined) {
      // No browser jump to the field: scrollIntoView moves it only if needed.
      setTimeout(() => {
        const input = container?.querySelector<HTMLInputElement>('input[inputmode="numeric"]')
        if (!input) return
        input.focus({ preventScroll: true })
        scrollIntoView(input, scroller)
      }, 200)
    }
  }
</script>

<StepTitle
  tag={t(`preset.steps.${step.id}.tag`)}
  title={t(`preset.steps.${step.id}.title`)}
  hint={t(`preset.steps.${step.id}.hint`, { car })}
/>

{#if step.submit && form.saveFailed}
  <div role="alert" class="banner">
    <span aria-hidden="true" class="banner-badge">!</span>
    <span class="banner-text">
      <span class="banner-title">{form.limited ? t('form.contact.limited_title') : t('form.contact.save_failed_title')}</span>
      <span class="banner-body">{form.limited ? t('form.contact.limited_text') : t('form.contact.save_failed_text')}</span>
    </span>
  </div>
{/if}

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  bind:this={container}
  class:stack={step.submit}
  class:pair={sideBySide}
  onfocusin={labelEnterKey}
  onkeydowncapture={enterToNextField}
>
  {#each shown as field, index (field.id)}
    {@const previous = shown[index - 1]}
    {#if field.widget === 'tiles'}
      <TilesField {field} dependents={dependentsOf(field)} {scroller} />
    {:else if field.widget === 'chips'}
      <ChipsField {field} {scroller} />
    {:else if field.widget === 'year_grid'}
      <YearGrid {field} onPicked={() => focusNextNumber(field)} />
    {:else if field.type === 'number'}
      <NumberField {field} {scroller} gap={previous ? '18px' : '0'} />
    {:else if field.type === 'select' && field.options.some((o) => o.level !== undefined)}
      <LevelSelect {field} />
    {:else if field.type === 'select'}
      <ChoiceGrid {field} />
    {:else if field.type === 'yes_no'}
      <YesNoField {field} {scroller} />
    {:else if field.format === 'vin'}
      <VinField {field} {scroller} />
    {:else}
      <TextField {field} {scroller} compact={sideBySide} marker={marker(field)} />
    {/if}
  {/each}
  {#if step.consent}<Consent />{/if}
  {#if step.submit}
    <!-- Honeypot: hidden from people and screen readers, filled in by bots.
         Not named like a contact field, so browser AutoFill leaves it alone. -->
    <input class="trap" type="text" name="referral_code" tabindex="-1" autocomplete="off" aria-hidden="true" bind:value={form.trap} />
  {/if}
</div>

{#if sideBySide}
  {#each shown as field (field.id)}
    {#if form.errors[field.id]}
      <div class="pair-error">
        <span role="alert" class="pair-alert"><span aria-hidden="true" class="pair-badge">!</span>{form.errorText(field.id)}</span>
      </div>
    {/if}
  {/each}
{/if}

{#if step.note === 'box'}
  <div data-st class="note-box"><span class="note-dot"></span><span>{t(`preset.steps.${step.id}.note`)}</span></div>
{:else if step.note === 'icon'}
  <div data-st class="note-icon">
    <span aria-hidden="true" class="ring"><span></span></span>
    <span>{t(`preset.steps.${step.id}.note`)}</span>
  </div>
{:else if step.note === 'text'}
  <p data-st class="note-text">{t(`preset.steps.${step.id}.note`)}</p>
{/if}

<style>
  .trap {
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    opacity: 0;
  }

  .stack {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .pair {
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr);
    gap: 10px;
  }

  .pair-error {
    margin-top: 10px;
  }

  .pair-alert {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 13.5px/1.35 var(--font-sans);
    color: var(--error);
    animation: ui-in 0.2s both;
  }

  .pair-badge {
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    background: var(--error);
    color: #111212;
    font: 700 11px/16px var(--font-sans);
    text-align: center;
  }

  .banner {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 14px 16px;
    border-radius: 16px;
    background: rgba(255, 138, 117, 0.08);
    border: 1px solid rgba(255, 138, 117, 0.35);
    margin-bottom: 18px;
    animation: ui-in 0.25s both;
  }

  .banner-badge {
    flex: none;
    width: 20px;
    height: 20px;
    border-radius: 10px;
    background: var(--error);
    color: #111212;
    font: 700 12px/20px var(--font-sans);
    text-align: center;
    margin-top: 1px;
  }

  .banner-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .banner-title {
    font: 600 15px/1.3 var(--font-sans);
    color: var(--error-soft);
  }

  .banner-body {
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .note-box {
    margin-top: 16px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 14px 16px;
    border-radius: 16px;
    background: var(--surface);
    border: 1px solid var(--line);
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .note-dot {
    flex: none;
    margin-top: 6px;
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--accent);
  }

  .note-icon {
    margin-top: 16px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  .ring {
    flex: none;
    margin-top: 2px;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1.5px solid var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ring span {
    width: 4px;
    height: 4px;
    border-radius: 2px;
    background: var(--text-muted);
  }

  .note-text {
    margin: 14px 0 0;
    font: 400 14px/1.5 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }
</style>
