<script lang="ts">
  // Settings: account security from the design, plus Help in the same style.
  // Notifications join this page with the push notifications stage.
  import { getContext } from 'svelte'
  import NotificationSettings from './NotificationSettings.svelte'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t

  let open = $state(false)
  const values = $state({ current: '', next: '', confirm: '' })
  let show = $state(false)
  let saving = $state(false)
  let failed = $state(false)
  let done = $state(false)
  let errors = $state<Record<string, string>>({})

  const requirements = $derived([
    { text: t('dashboard.settings.req_length'), ok: values.next.length >= 8 },
    { text: t('dashboard.settings.req_number'), ok: /\d/.test(values.next) },
  ])

  function toggle() {
    open = !open
    values.current = values.next = values.confirm = ''
    errors = {}
    failed = false
    done = false
  }

  async function submit() {
    const { current, next, confirm } = values
    const found: Record<string, string> = {}
    if (!current) found.current = 'current_required'
    if (next.length < 8 || !/\d/.test(next)) found.next = 'weak'
    else if (next === current) found.next = 'same'
    if (!confirm) found.confirm = 'confirm_required'
    else if (confirm !== next) found.confirm = 'mismatch'
    errors = found
    if (Object.keys(found).length) return
    saving = true
    failed = false
    const problem = await dash.changePassword(current, next)
    saving = false
    if (!problem) {
      open = false
      done = true
      show = false
      values.current = values.next = values.confirm = ''
    } else if (problem === 'wrong_current') errors = { current: problem }
    else if (problem === 'weak' || problem === 'same' || problem === 'given') errors = { next: problem }
    else failed = true
  }

  const fields = [
    { key: 'current' as const, label: 'dashboard.settings.current', autocomplete: 'current-password' as const },
    { key: 'next' as const, label: 'dashboard.settings.new', autocomplete: 'new-password' as const },
    { key: 'confirm' as const, label: 'dashboard.settings.confirm', autocomplete: 'new-password' as const },
  ]
  const helpTopics = ['arrive', 'statuses', 'retention', 'sources']
</script>

<div class="page" style:padding={dash.desk ? '36px 40px 64px' : '20px 16px 32px'}>
  <div class="head">
    <h1 style:font-size={dash.desk ? '40px' : '32px'}>{t('dashboard.settings.title')}</h1>
    <p>{t('dashboard.settings.subtitle')}</p>
  </div>

  <NotificationSettings columns={dash.desk ? '220px minmax(0, 1fr)' : 'minmax(0, 1fr)'} />

  <section style:grid-template-columns={dash.desk ? '220px minmax(0, 1fr)' : 'minmax(0, 1fr)'}>
    <div class="about">
      <h2>{t('dashboard.settings.security_title')}</h2>
      <span>{t('dashboard.settings.security_text')}</span>
    </div>
    <div class="card">
      <div class="line">
        <div class="pair">
          <span class="item">{t('dashboard.settings.password')}</span>
          {#if dash.passwordChangedAt}
            <span class="meta">{t('dashboard.settings.password_changed', { when: dash.fmt.when(dash.passwordChangedAt) })}</span>
          {/if}
        </div>
        <button class="outline" aria-expanded={open} disabled={saving} onclick={toggle}>
          {open ? t('dashboard.settings.cancel') : t('dashboard.settings.change')}
        </button>
      </div>
      {#if done}
        <div role="status" class="ok">
          <span aria-hidden="true" class="ok-mark"><svg width="10" height="10" viewBox="0 0 10 10"><path d="M2 5.2l2 2L8 3" style="stroke: var(--on-accent)" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round" /></svg></span>
          <span>{t('dashboard.settings.updated')}</span>
        </div>
      {/if}
      {#if open}
        <div class="form">
          {#if failed}
            <div role="alert" class="fail">
              <span aria-hidden="true" class="badge">!</span>
              <span class="fail-text">
                <span class="fail-title">{t('dashboard.settings.failed_title')}</span>
                <span>{t('dashboard.settings.failed_text')}</span>
              </span>
            </div>
          {/if}
          {#each fields as field (field.key)}
            <label class="field">
              <span class="label">{t(field.label)}</span>
              <input
                type={show ? 'text' : 'password'}
                bind:value={values[field.key]}
                oninput={() => {
                  const copy = { ...errors }
                  delete copy[field.key]
                  errors = copy
                }}
                onkeydown={(event) => event.key === 'Enter' && submit()}
                autocomplete={field.autocomplete}
                aria-invalid={Boolean(errors[field.key])}
                class:invalid={errors[field.key]}
                disabled={saving}
              />
              {#if errors[field.key]}
                <span role="alert" class="error"><span aria-hidden="true" class="err-badge">!</span>{t(`dashboard.settings.errors.${errors[field.key]}`)}</span>
              {/if}
              {#if field.key === 'next'}
                <span class="reqs">
                  {#each requirements as requirement (requirement.text)}
                    <span class="req" class:met={requirement.ok}><span class="req-dot"></span>{requirement.text}</span>
                  {/each}
                </span>
              {/if}
            </label>
          {/each}
          <div class="form-row">
            <button class="link" onclick={() => (show = !show)}>{show ? t('dashboard.settings.hide') : t('dashboard.settings.show')}</button>
            <button class="primary" disabled={saving} onclick={submit}>
              {#if saving}<span aria-hidden="true" class="spinner"></span>{/if}
              {saving ? t('dashboard.settings.updating') : t('dashboard.settings.update')}
            </button>
          </div>
        </div>
      {/if}
      <div class="line top-border">
        <div class="pair">
          <span class="item">{t('dashboard.settings.logout_title')}</span>
          <span class="meta">{t('dashboard.settings.logout_text')}</span>
        </div>
        <button class="outline danger" onclick={() => (dash.logoutOpen = true)}>{t('dashboard.settings.logout')}</button>
      </div>
    </div>
  </section>

  <section style:grid-template-columns={dash.desk ? '220px minmax(0, 1fr)' : 'minmax(0, 1fr)'}>
    <div class="about">
      <h2>{t('dashboard.settings.help_title')}</h2>
      <span>{t('dashboard.settings.help_text')}</span>
    </div>
    <div class="card">
      {#each helpTopics as topic, index (topic)}
        <div class="help" class:top-border={index > 0}>
          <span class="item">{t(`dashboard.settings.help.${topic}.title`, { days: dash.config.retentionDays })}</span>
          <span class="help-text">{t(`dashboard.settings.help.${topic}.text`, { days: dash.config.retentionDays })}</span>
        </div>
      {/each}
    </div>
  </section>
</div>

<style>
  .page {
    max-width: 980px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .head {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  h1 {
    margin: 0;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
  }

  p {
    margin: 0;
    font: 400 15px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  section {
    display: grid;
    gap: 14px 32px;
    padding-top: 24px;
    border-top: 1px solid #222424;
  }

  .about {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  h2 {
    margin: 0;
    font: 600 15.5px/1.2 var(--font-sans);
  }

  .about span {
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .card {
    display: flex;
    flex-direction: column;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    padding: 16px 18px;
  }

  .top-border {
    border-top: 1px solid var(--line-soft);
  }

  .pair {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .item {
    font: 500 14.5px/1.3 var(--font-sans);
  }

  .meta {
    font: 400 13px/1.4 var(--font-sans);
    color: var(--text-muted);
  }

  .outline {
    flex: none;
    height: 42px;
    padding: 0 15px;
    border-radius: 12px;
    border: 1px solid var(--line-strong);
    background: transparent;
    color: var(--text);
    font: 500 14.5px/1 var(--font-sans);
    cursor: pointer;
    transition:
      background-color 0.15s,
      border-color 0.15s;
  }

  .outline:hover {
    background: var(--surface-2);
  }

  .outline.danger {
    color: var(--error);
  }

  .outline.danger:hover {
    background: rgba(255, 138, 117, 0.08);
    border-color: rgba(255, 138, 117, 0.4);
  }

  .ok {
    margin: 0 18px 16px;
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgb(var(--accent-rgb) / 0.06);
    border: 1px solid rgb(var(--accent-rgb) / 0.3);
    font: 400 13.5px/1.45 var(--font-sans);
    color: #e4e3dd;
    animation: ui-in 0.25s both;
  }

  .ok-mark {
    flex: none;
    width: 18px;
    height: 18px;
    border-radius: 9px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 16px 18px 18px;
    border-top: 1px solid var(--line-soft);
    animation: ui-in 0.25s both;
  }

  .fail {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(255, 138, 117, 0.08);
    border: 1px solid rgba(255, 138, 117, 0.35);
  }

  .badge {
    flex: none;
    width: 18px;
    height: 18px;
    border-radius: 9px;
    background: var(--error);
    color: #111212;
    font: 700 11px/18px var(--font-sans);
    text-align: center;
  }

  .fail-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
    font: 400 13.5px/1.45 var(--font-sans);
    color: var(--text-soft);
  }

  .fail-title {
    font: 600 14px/1.3 var(--font-sans);
    color: var(--error-soft);
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

  input {
    height: 48px;
    padding: 0 14px;
    border-radius: 12px;
    border: 1.5px solid var(--line-strong);
    background: var(--bg);
    font: 400 16px var(--font-sans);
    outline: none;
    transition:
      border-color 0.15s,
      box-shadow 0.15s;
  }

  input.invalid {
    border-color: var(--error);
  }

  input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgb(var(--accent-rgb) / 0.18);
  }

  .error {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 13px/1.35 var(--font-sans);
    color: var(--error);
  }

  .err-badge {
    flex: none;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    background: var(--error);
    color: #111212;
    font: 700 11px/16px var(--font-sans);
    text-align: center;
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

  .form-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 4px;
  }

  .link {
    height: 40px;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--text);
    font: 500 14px/1 var(--font-sans);
    text-decoration: underline;
    text-underline-offset: 4px;
    text-decoration-color: var(--text-faint);
    cursor: pointer;
  }

  .primary {
    height: 46px;
    padding: 0 18px;
    border: 0;
    border-radius: 12px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 15px/1 var(--font-sans);
    display: flex;
    align-items: center;
    gap: 9px;
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .primary:hover {
    background: var(--accent-hover);
  }

  .primary:active {
    transform: scale(0.97);
  }

  .spinner {
    width: 15px;
    height: 15px;
    border-radius: 8px;
    border: 2px solid rgb(var(--on-accent-rgb) / 0.25);
    border-top-color: var(--on-accent);
    animation: ui-spin 0.7s linear infinite;
  }

  .help {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 16px 18px;
  }

  .help-text {
    font: 400 14px/1.5 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }
</style>
