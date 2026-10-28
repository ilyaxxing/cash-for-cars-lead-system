<script lang="ts">
  // Consent to processing, required before the lead is saved. Names the
  // operator from the instance settings and links to the privacy policy.
  import { getContext } from 'svelte'
  import ErrorText from '../ErrorText.svelte'
  import type { FormState } from '../state.svelte'

  const form = getContext<FormState>('form')
  const t = form.t
  const invalid = $derived(Boolean(form.errors.consent))

  function toggle(event: Event & { currentTarget: HTMLInputElement }) {
    form.consent = event.currentTarget.checked
    if (form.errors.consent) {
      const errors = { ...form.errors }
      delete errors.consent
      form.errors = errors
    }
  }
</script>

<label data-st class="consent" class:invalid>
  <input
    type="checkbox"
    checked={form.consent}
    onchange={toggle}
    disabled={form.busy}
    aria-required="true"
    aria-invalid={invalid}
    aria-describedby="consent-text"
  />
  <span aria-hidden="true" class="box" class:on={form.consent} class:invalid>
    {#if form.consent}
      <svg width="14" height="14" viewBox="0 0 14 14">
        <path
          d="M3 7.3l2.6 2.6L11 4.4"
          style="stroke: var(--on-accent)"
          stroke-width="2"
          fill="none"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    {/if}
  </span>
  <span id="consent-text" class="text">
    {t('form.contact.consent', { operator: form.config.operator })}
    <a href={form.config.privacyUrl} target="_blank" rel="noopener">{t('form.contact.consent_link')}</a>.
  </span>
</label>
{#if invalid}
  <div class="error"><ErrorText text={t('form.contact.consent_error')} /></div>
{/if}

<style>
  .consent {
    position: relative;
    display: flex;
    gap: 14px;
    align-items: flex-start;
    padding: 16px;
    border-radius: 16px;
    border: 1.5px solid #2e3030;
    background: var(--surface);
    cursor: pointer;
    transition: border-color 0.15s;
  }

  .consent.invalid {
    border-color: var(--error);
  }

  input {
    position: absolute;
    opacity: 0;
    width: 1px;
    height: 1px;
    margin: 0;
  }

  .box {
    flex: none;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    border: 1.5px solid var(--line-hover);
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    transition:
      background-color 0.15s,
      border-color 0.15s;
  }

  .box.on {
    background: var(--accent);
    border-color: var(--accent);
  }

  .box.invalid {
    border-color: var(--error);
  }

  .box svg {
    animation: ui-chip 0.18s both;
  }

  input:focus-visible + .box {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }

  .text {
    font: 400 14.5px/1.45 var(--font-sans);
    color: var(--text);
    text-wrap: pretty;
  }

  .error {
    margin-top: -6px;
  }
</style>
