<script lang="ts">
  // VIN entry: upper case, letters and digits only, with a 17-character counter.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import { cleanVin } from '../engine'
  import ErrorText from '../ErrorText.svelte'
  import { scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'

  let { field, scroller }: { field: FieldSpec; scroller?: HTMLElement } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const value = $derived(String(form.answers[field.id] ?? ''))
  const error = $derived(form.errorText(field.id))

  function onInput(event: Event & { currentTarget: HTMLInputElement }) {
    const clean = cleanVin(event.currentTarget.value)
    event.currentTarget.value = clean
    form.set(field.id, clean)
  }
</script>

<label data-st class="stack">
  <span class="label-row"><span>{form.fieldLabel(field)}</span><span>{t('form.labels.optional')}</span></span>
  <input
    class="field-input"
    class:invalid={error}
    {value}
    oninput={onInput}
    onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
    onkeydown={(event) => event.key === 'Enter' && (event.preventDefault(), form.next())}
    maxlength="17"
    autocomplete="off"
    autocapitalize="characters"
    spellcheck="false"
    placeholder={t(`preset.fields.${field.id}.placeholder`)}
    aria-invalid={Boolean(error)}
  />
  <span class="count" class:full={value.length === 17}>{value.length}/17</span>
  <ErrorText text={error} />
</label>

<style>
  .stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  input {
    height: 64px;
    padding: 0 18px;
    border-radius: 16px;
    font: 500 17px var(--font-mono);
    letter-spacing: 0.06em;
  }

  /* The wide monospace suits the VIN itself; the hint in it would not fit
     a phone's width. */
  input::placeholder {
    font: 400 16px var(--font-sans);
    letter-spacing: 0;
  }

  .count {
    display: flex;
    justify-content: flex-end;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .count.full {
    color: var(--accent);
  }
</style>
