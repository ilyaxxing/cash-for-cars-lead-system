<script lang="ts">
  // Big number entry: mileage with its unit chip, or a price with the
  // currency symbol, before or after the amount as the country writes it.
  // Digits are grouped as the seller types.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../../shared/config'
  import { digitsOnly, maxDigits } from '../engine'
  import ErrorText from '../ErrorText.svelte'
  import { scrollIntoView } from '../motion'
  import type { FormState } from '../state.svelte'

  let {
    field,
    scroller,
    gap = '0',
    input = $bindable(),
  }: { field: FieldSpec; scroller?: HTMLElement; gap?: string; input?: HTMLInputElement } = $props()
  const form = getContext<FormState>('form')
  const t = form.t

  const money = $derived(field.unit === 'currency')
  const value = $derived(form.answers[field.id])
  const shown = $derived(typeof value === 'number' ? form.formatNumber(value) : '')
  const error = $derived(form.errorText(field.id))

  function onInput(event: Event & { currentTarget: HTMLInputElement }) {
    const digits = digitsOnly(event.currentTarget.value, maxDigits(field))
    const number = digits ? Number(digits) : undefined
    form.set(field.id, number)
    event.currentTarget.value = number === undefined ? '' : form.formatNumber(number)
  }
</script>

<label data-st class="stack" style:margin-top={gap}>
  <span class="label head">
    {money
      ? t('form.labels.price', { label: form.fieldLabel(field), currency: form.config.currency })
      : form.fieldLabel(field)}
  </span>
  <span class="box" class:money class:invalid={error}>
    {#if money && !form.currencyAfter}<span aria-hidden="true" class="symbol">{form.currencySymbol}</span>{/if}
    <input
      bind:this={input}
      value={shown}
      oninput={onInput}
      onfocus={(event) => scrollIntoView(event.currentTarget, scroller)}
      onkeydown={(event) => event.key === 'Enter' && (event.preventDefault(), form.next())}
      inputmode="numeric"
      placeholder="0"
      autocomplete="off"
      aria-invalid={Boolean(error)}
    />
    {#if money && form.currencyAfter}<span aria-hidden="true" class="symbol">{form.currencySymbol}</span>{/if}
    {#if !money}<span class="unit">{form.unit('short')}</span>{/if}
  </span>
  {#if !money}
    <span class="help">{t(`preset.fields.${field.id}.help`, { unit_long: form.unit('long') })}</span>
  {/if}
</label>
<div class="error"><ErrorText text={error} gap="10px" /></div>

<style>
  .stack {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .head {
    font: 500 13.5px/1 var(--font-sans);
  }

  .box {
    display: flex;
    align-items: center;
    gap: 12px;
    height: 76px;
    padding: 0 20px;
    border-radius: 18px;
    border: 1.5px solid var(--line-strong);
    background: var(--surface);
    transition: border-color 0.15s;
  }

  .box:focus-within {
    border-color: var(--accent);
  }

  .box.invalid {
    border-color: var(--error);
  }

  .box.money {
    height: 84px;
    border-radius: 20px;
  }

  .symbol {
    font: 600 36px/1 var(--font-sans);
    color: var(--text-muted);
  }

  input {
    flex: 1;
    min-width: 0;
    border: 0;
    background: transparent;
    outline: none;
    padding: 0;
    font: 600 36px/1 var(--font-sans);
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
  }

  .money input {
    font-size: 40px;
  }

  .unit {
    flex: none;
    height: 30px;
    padding: 0 10px;
    border-radius: 8px;
    background: var(--surface-2);
    border: 1px solid var(--line-strong);
    font: 500 13px/28px var(--font-mono);
    color: var(--text);
  }

  .help {
    font: 400 13px/1.4 var(--font-sans);
    color: var(--text-muted);
  }
</style>
