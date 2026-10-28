<script lang="ts">
  // Plain text, phone and email inputs, with an optional Required/Optional
  // marker next to the label (used on the contact step).
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import ErrorText from '../ErrorText.svelte'
  import { scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'

  let {
    field,
    scroller,
    compact = false,
    marker = '',
  }: { field: FieldSpec; scroller?: HTMLElement; compact?: boolean; marker?: string } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const value = $derived(form.answers[field.id])
  const error = $derived(form.errorText(field.id))
  const kind = $derived(
    field.type === 'phone'
      ? { type: 'tel', inputmode: 'tel', autocomplete: 'tel' }
      : field.format === 'email'
        ? { type: 'email', inputmode: 'email', autocomplete: 'email' }
        : field.format === 'postal_code'
          ? { type: 'text', inputmode: 'numeric', autocomplete: 'postal-code' }
          : {
              type: 'text',
              inputmode: 'text',
              autocomplete: field.id === 'name' ? 'name' : field.id === 'location' ? 'address-level2' : 'off',
            },
  ) as { type: string; inputmode: 'tel' | 'email' | 'numeric' | 'text'; autocomplete: AutoFill }
</script>

<label data-st class="stack" class:compact>
  {#if marker}
    <span class="label-row"><span>{form.fieldLabel(field)}</span><span>{marker}</span></span>
  {:else}
    <span class="label">{form.fieldLabel(field)}</span>
  {/if}
  <input
    class="field-input"
    class:invalid={error}
    class:mono={field.format === 'postal_code'}
    type={kind.type}
    inputmode={kind.inputmode}
    autocomplete={kind.autocomplete}
    value={value ?? ''}
    oninput={(event) => form.set(field.id, event.currentTarget.value)}
    onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
    onkeydown={(event) => event.key === 'Enter' && (event.preventDefault(), form.next())}
    placeholder={t(`preset.fields.${field.id}.placeholder`)}
    disabled={form.busy}
    aria-required={field.required}
    aria-invalid={Boolean(error)}
  />
  {#if !compact}<ErrorText text={error} />{/if}
</label>

<style>
  .stack {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }

  input {
    width: 100%;
    height: 56px;
    padding: 0 16px;
    border-radius: 14px;
    font: 400 17px var(--font-sans);
  }

  .compact input {
    height: 58px;
  }

  input.mono {
    font-family: var(--font-mono);
  }
</style>
