<script lang="ts">
  // Sign-in, and the password of the owner's own that replaces the one handed
  // over. Not in the design; built from its log-out screen and form fields,
  // with the password rules of Settings.
  import { getContext } from 'svelte'
  import BrandMark from '../shared/BrandMark.svelte'
  import TagGlyph from '../shared/TagGlyph.svelte'
  import type { DashboardState } from './state.svelte'

  let { loggedOut = false, choose = false }: { loggedOut?: boolean; choose?: boolean } = $props()
  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const brand = dash.config.brand

  // svelte-ignore state_referenced_locally
  let showForm = $state(!loggedOut)
  let password = $state('')
  let show = $state(false)
  let busy = $state(false)
  let error = $state('')

  async function submit(event: SubmitEvent) {
    event.preventDefault()
    if (!password) {
      error = 'empty'
      return
    }
    busy = true
    error = (await dash.signIn(password)) ?? ''
    busy = false
  }

  // The owner's own password, with the rules the server applies.
  let next = $state('')
  let confirm = $state('')
  let errors = $state<{ next?: string; confirm?: string; form?: string }>({})
  const requirements = $derived([
    { text: t('dashboard.settings.req_length'), ok: next.length >= 8 },
    { text: t('dashboard.settings.req_number'), ok: /\d/.test(next) },
  ])

  async function save(event: SubmitEvent) {
    event.preventDefault()
    const found: typeof errors = {}
    if (next.length < 8 || !/\d/.test(next)) found.next = 'weak'
    if (!confirm) found.confirm = 'confirm_required'
    else if (confirm !== next) found.confirm = 'mismatch'
    errors = found
    if (found.next || found.confirm) return
    busy = true
    const problem = await dash.setOwnPassword(next)
    busy = false
    if (problem === 'weak' || problem === 'given' || problem === 'same') errors = { next: problem === 'same' ? 'given' : problem }
    else if (problem) errors = { form: 'network' }
  }
</script>

{#snippet logo()}
  {#if brand.logo}
    <img class="client-logo" class:wordmark={brand.logo.wordmark} src={brand.logo.url} alt={brand.logo.wordmark ? brand.name : ''} />
  {:else}
    <span class="logo" aria-hidden="true"><TagGlyph dollar /></span>
  {/if}
{/snippet}

{#snippet problem(code: string | undefined, key: string)}
  {#if code}
    <span role="alert" class="error"><span aria-hidden="true" class="badge">!</span>{t(`${key}.${code}`)}</span>
  {/if}
{/snippet}

<div class="screen">
  {#if choose}
    <form class="center form" onsubmit={save} novalidate>
      {@render logo()}
      <div class="words">
        <h1 class="title">{t('dashboard.new_password.title')}</h1>
        <span class="text">{t('dashboard.new_password.text')}</span>
      </div>
      <label class="field">
        <span class="label">{t('dashboard.settings.new')}</span>
        <span class="input-row">
          <!-- svelte-ignore a11y_autofocus -->
          <input
            type={show ? 'text' : 'password'}
            bind:value={next}
            oninput={() => (errors = { ...errors, next: undefined, form: undefined })}
            autocomplete="new-password"
            autofocus
            aria-invalid={Boolean(errors.next)}
            class:invalid={errors.next}
            disabled={busy}
          />
          <button type="button" class="toggle" onclick={() => (show = !show)}>{show ? t('dashboard.login.hide') : t('dashboard.login.show')}</button>
        </span>
        {@render problem(errors.next, 'dashboard.settings.errors')}
        <span class="reqs">
          {#each requirements as requirement (requirement.text)}
            <span class="req" class:met={requirement.ok}><span class="req-dot"></span>{requirement.text}</span>
          {/each}
        </span>
      </label>
      <label class="field">
        <span class="label">{t('dashboard.settings.confirm')}</span>
        <input
          type={show ? 'text' : 'password'}
          bind:value={confirm}
          oninput={() => (errors = { ...errors, confirm: undefined, form: undefined })}
          autocomplete="new-password"
          enterkeyhint="done"
          aria-invalid={Boolean(errors.confirm)}
          class:invalid={errors.confirm}
          disabled={busy}
        />
        {@render problem(errors.confirm, 'dashboard.settings.errors')}
      </label>
      {@render problem(errors.form, 'dashboard.login.errors')}
      <button type="submit" class="primary" disabled={busy}>
        {#if busy}<span aria-hidden="true" class="spinner"></span>{/if}
        {busy ? t('dashboard.new_password.saving') : t('dashboard.new_password.submit')}
      </button>
    </form>
  {:else if !showForm}
    <div class="center">
      {@render logo()}
      <div class="words">
        <span class="title">{t('dashboard.logout.done_title')}</span>
        <span class="text">{t('dashboard.logout.done_text')}</span>
      </div>
      <button class="primary inline" onclick={() => (showForm = true)}>{t('dashboard.logout.again')}</button>
    </div>
  {:else}
    <form class="center form" onsubmit={submit} novalidate>
      {@render logo()}
      <div class="words">
        {#if !brand.logo?.wordmark}
          <span class="brand"><BrandMark {brand} size="small" mark={false} /></span>
        {/if}
        <h1 class="title">{t('dashboard.login.title')}</h1>
        <span class="text">{t('dashboard.login.text')}</span>
      </div>
      <label class="field">
        <span class="label">{t('dashboard.login.password')}</span>
        <span class="input-row">
          <!-- svelte-ignore a11y_autofocus -->
          <input
            type={show ? 'text' : 'password'}
            bind:value={password}
            oninput={() => (error = '')}
            autocomplete="current-password"
            enterkeyhint="go"
            autofocus
            aria-invalid={Boolean(error)}
            class:invalid={error}
            disabled={busy}
          />
          <button type="button" class="toggle" onclick={() => (show = !show)}>{show ? t('dashboard.login.hide') : t('dashboard.login.show')}</button>
        </span>
        {#if error}
          <span role="alert" class="error"><span aria-hidden="true" class="badge">!</span>{t(`dashboard.login.errors.${error}`)}</span>
        {/if}
      </label>
      <button type="submit" class="primary" disabled={busy}>
        {#if busy}<span aria-hidden="true" class="spinner"></span>{/if}
        {busy ? t('dashboard.login.signing') : t('dashboard.login.submit')}
      </button>
    </form>
  {/if}
</div>

<style>
  .screen {
    height: 100%;
    background: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: ui-fade 0.25s both;
  }

  /* On a phone the form sits high, so the keyboard (about the lower half of
     the screen) never covers the password field or Sign in. */
  @media (max-width: 767px) {
    .screen {
      align-items: flex-start;
      padding-top: max(56px, 9vh);
    }
  }

  .center {
    width: 100%;
    max-width: 380px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
    text-align: center;
  }

  .form {
    align-items: stretch;
    text-align: left;
  }

  .logo {
    align-self: center;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .client-logo {
    align-self: center;
    display: block;
    width: auto;
    height: 56px;
    max-width: 240px;
    object-fit: contain;
  }

  .client-logo.wordmark {
    height: 44px;
  }

  .words {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .form .words {
    align-items: center;
    text-align: center;
  }

  .brand {
    margin-bottom: 4px;
  }

  .title {
    margin: 0;
    font: 700 26px/1.1 var(--font-sans);
    letter-spacing: -0.03em;
  }

  .text {
    font: 400 15px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .label {
    font: 500 13.5px/1.3 var(--font-sans);
    color: var(--text-muted);
  }

  .input-row {
    position: relative;
    display: flex;
  }

  input {
    flex: 1;
    min-width: 0;
    height: 52px;
    padding: 0 76px 0 14px;
    border-radius: 12px;
    border: 1.5px solid var(--line-strong);
    background: var(--surface);
    font: 400 16px var(--font-sans);
    outline: none;
    transition:
      border-color 0.15s,
      box-shadow 0.15s;
  }

  /* The confirm field stands alone, without the Show button's row. */
  .field > input {
    flex: none;
    padding-right: 14px;
  }

  input.invalid {
    border-color: var(--error);
  }

  .reqs {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    font: 500 11.5px/1 var(--font-mono);
  }

  .req {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-faint);
  }

  .req.met {
    color: var(--text);
  }

  .req-dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: #3a3c3c;
  }

  .req.met .req-dot {
    background: var(--accent);
  }

  input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgb(var(--accent-rgb) / 0.18);
  }

  .toggle {
    position: absolute;
    right: 6px;
    top: 6px;
    height: 40px;
    padding: 0 12px;
    border: 0;
    border-radius: 9px;
    background: transparent;
    color: var(--text-muted);
    font: 500 13.5px/1 var(--font-sans);
    cursor: pointer;
  }

  .toggle:hover {
    background: var(--surface-2);
    color: var(--text);
  }

  .error {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 13.5px/1.35 var(--font-sans);
    color: var(--error);
    animation: ui-in 0.2s both;
  }

  .badge {
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    background: var(--error);
    color: #111212;
    font: 700 11px/16px var(--font-sans);
    text-align: center;
  }

  .primary {
    height: 52px;
    border: 0;
    border-radius: 14px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 16px/1 var(--font-sans);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .primary.inline {
    height: 50px;
    padding: 0 22px;
  }

  .primary:hover {
    background: var(--accent-hover);
  }

  .primary:active {
    transform: scale(0.98);
  }

  .spinner {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid rgb(var(--on-accent-rgb) / 0.25);
    border-top-color: var(--on-accent);
    animation: ui-spin 0.7s linear infinite;
  }
</style>
