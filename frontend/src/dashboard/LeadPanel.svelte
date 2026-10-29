<script lang="ts">
  // The open lead: status, photos, the car's answers, seller contact,
  // notes and activity. A side panel on wide screens, full screen on phones.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../shared/config'
  import { formatPhone } from '../shared/region'
  import type { Status } from './api'
  import { summarize } from './car'
  import { reply } from './contact'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  const present = dash.present
  const STATUSES: Status[] = ['new', 'in_work', 'bought', 'rejected']

  let draft = $state('')
  let copied = $state(false)
  let scroller: HTMLDivElement | undefined = $state()

  const lead = $derived(dash.detail)
  const car = $derived(lead ? summarize(present, lead) : null)
  const panelWidth = $derived(dash.desk ? Math.min(800, dash.width - 80) : dash.width)
  const position = $derived(dash.navIds.indexOf(dash.openId ?? -1))
  const purged = $derived(Boolean(lead?.purgedAt))

  const steps = dash.config.preset.steps.filter((step) => step.enabled)
  const submitIndex = steps.findIndex((step) => step.submit)
  // Answers about the car: everything asked before the contact step.
  const carFields = steps
    .slice(0, submitIndex)
    .flatMap((step) => step.fields)
    .filter((field) => field.type !== 'photos')
  const contactFields = steps[submitIndex]?.fields ?? []
  const phoneField = contactFields.find((field) => field.type === 'phone')
  const emailField = contactFields.find((field) => field.format === 'email')
  const nameField = contactFields.find((field) => field.id === 'name')
  const methodField = contactFields.find((field) => field.type === 'select')
  const photoSlots = dash.config.preset.steps.flatMap((step) => step.fields).find((f) => f.type === 'photos')?.slots ?? []

  function rowValue(field: FieldSpec): { text: string; flag: boolean; missing: boolean } {
    const value = lead?.answers[field.id]
    let text = present.display(field, value)
    if (!text) return { text: t('dashboard.lead.not_provided'), flag: false, missing: true }
    for (const child of field.follow_up && value === field.follow_up.when ? field.follow_up.fields : []) {
      const extra = lead?.answers[child.id]
      if (extra) text += ` · ${extra}`
    }
    return { text, flag: Boolean(field.flag && value === field.flag), missing: false }
  }

  function photoLabel(index: number): string {
    const photo = lead?.photos[index]
    if (photo?.slot) return t(`preset.photos.${photo.slot}.label`)
    const extras = lead?.photos.slice(0, index + 1).filter((p) => !p.slot).length ?? 1
    return t('dashboard.lead.extra_photo', { n: extras })
  }

  const pad2 = (n: number) => String(n).padStart(2, '0')
  const phone = $derived(String(lead?.answers[phoneField?.id ?? ''] ?? ''))
  const email = $derived(String(lead?.answers[emailField?.id ?? ''] ?? ''))
  const name = $derived(String(lead?.answers[nameField?.id ?? ''] ?? ''))
  const subject = $derived(car ? t('dashboard.lead.email_subject', { car: car.title }) : '')
  const mail = $derived(`mailto:${email}?subject=${encodeURIComponent(subject)}`)
  const answer = $derived(reply(lead?.answers[methodField?.id ?? ''], phone, email, subject))
  // A web link opens in a new tab; a text or an email opens the phone's own app.
  const target = $derived(answer.href.startsWith('https:') ? '_blank' : undefined)
  const lastChange = $derived(lead?.events[0])

  async function copyPhone() {
    try {
      await navigator.clipboard.writeText(phone)
    } catch {
      // clipboard blocked: the number is on screen anyway
    }
    copied = true
    setTimeout(() => (copied = false), 1800)
  }

  async function submitNote() {
    if (await dash.addNote(draft)) draft = ''
  }

  $effect(() => {
    void dash.openId
    if (scroller) scroller.scrollTop = 0
    draft = ''
  })
</script>

<div class="overlay">
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="backdrop" aria-hidden="true" onclick={() => dash.close()}></div>
  <div class="panel" role="dialog" aria-modal="true" aria-label={car?.title ?? ''} style:width="{panelWidth}px">
    <div class="bar" style:padding={dash.desk ? '0 16px 0 12px' : '0 12px 0 6px'}>
      <button class="icon-button" aria-label={t('dashboard.lead.close')} onclick={() => dash.close()}>
        {#if dash.desk}
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8" stroke="#F4F3EE" stroke-width="1.6" stroke-linecap="round" /></svg>
        {:else}
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M12.5 4.5L7 10l5.5 5.5" stroke="#F4F3EE" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
        {/if}
      </button>
      <span class="id">#{dash.openId}</span>
      <span class="grow"></span>
      {#if position >= 0}<span class="pos">{t('dashboard.lead.position', { n: position + 1, total: dash.navIds.length })}</span>{/if}
      <button class="step" aria-label={t('dashboard.lead.previous')} disabled={position <= 0} onclick={() => dash.step(-1)}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3.5 8.5L7 5l3.5 3.5" stroke="#F4F3EE" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
      <button class="step" aria-label={t('dashboard.lead.next')} disabled={position < 0 || position >= dash.navIds.length - 1} onclick={() => dash.step(1)}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M3.5 5.5L7 9l3.5-3.5" stroke="#F4F3EE" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
      </button>
    </div>

    <div class="scroll" bind:this={scroller}>
      {#if lead && car}
        <div class="content" style:padding={dash.desk ? '28px 32px 48px' : '20px 16px 28px'}>
          <div class="top">
            <div class="chips">
              <span class="chip status-{lead.status}"><span class="status-dot"></span>{dash.statusLabel(lead.status)}</span>
              <span class="source">{lead.sourceLabel}</span>
              <span class="received">{t('dashboard.lead.received', { when: dash.fmt.when(lead.createdAt) })}</span>
            </div>
            <div class="title-row">
              <div class="title-block">
                <h2 style:font-size={dash.desk ? '38px' : '30px'}>{car.title}</h2>
                <span class="sub">{car.sub}</span>
              </div>
              <div class="price-block" style:align-items={panelWidth >= 560 ? 'flex-end' : 'flex-start'}>
                <span class="mono-label small">{t('dashboard.lead.asking_price')}</span>
                {#if car.price}
                  <span class="price" style:font-size={dash.desk ? '34px' : '28px'}>{car.price}</span>
                {:else}
                  <span class="no-price">{t('dashboard.lead.not_provided')}</span>
                {/if}
              </div>
            </div>
          </div>

          <div class="box">
            <div class="box-head">
              <span id="status-label" class="box-title">{t('dashboard.lead.status_title')}</span>
              <span class="box-meta">{lastChange ? t('dashboard.lead.updated', { when: dash.fmt.when(lastChange.createdAt) }) : t('dashboard.lead.not_processed')}</span>
            </div>
            <div role="radiogroup" aria-labelledby="status-label" class="options" style:grid-template-columns={panelWidth >= 560 ? 'repeat(4, minmax(0, 1fr))' : 'repeat(2, minmax(0, 1fr))'}>
              {#each STATUSES as status (status)}
                {@const on = lead.status === status}
                <button role="radio" aria-checked={on} class="option status-{status}" class:on onclick={() => dash.requestStatus(status)}>
                  <span class="status-dot option-dot"></span>{dash.statusLabel(status)}
                </button>
              {/each}
            </div>
          </div>

          <div class="section">
            <div class="section-head">
              <span class="mono-label">{lead.photos.length ? t('dashboard.lead.photos_count', { count: lead.photos.length }) : t('dashboard.lead.photos')}</span>
              {#if lead.photos.length}<span class="hint">{t('dashboard.lead.enlarge_hint')}</span>{/if}
            </div>
            {#if lead.photos.length}
              <button class="main-photo" aria-label={t('dashboard.lead.enlarge_aria', { n: 1, label: photoLabel(0) })} onclick={() => (dash.lightbox = 0)}>
                <img src={lead.photos[0].url} alt={`${car.title}, ${present.lower(photoLabel(0))}`} />
                <span class="tag">{t('dashboard.lead.photo_tag', { n: pad2(1), label: photoLabel(0) })}</span>
              </button>
              {#if lead.photos.length > 1}
                <div class="thumbs">
                  {#each lead.photos.slice(1, 6) as photo, index (photo.id)}
                    {@const n = index + 2}
                    <button class="thumb" aria-label={t('dashboard.lead.enlarge_aria', { n, label: photoLabel(n - 1) })} onclick={() => (dash.lightbox = n - 1)}>
                      <img src={photo.thumbUrl} alt="" loading="lazy" />
                      <span class="thumb-num">{pad2(n)}</span>
                      {#if index === 4 && lead.photos.length > 6}<span class="thumb-more">+{lead.photos.length - 6}</span>{/if}
                    </button>
                  {/each}
                </div>
              {/if}
            {:else}
              <div class="no-photos">
                {purged && lead.hasPhotos ? t('dashboard.lead.photos_purged', { days: dash.config.retentionDays }) : t('dashboard.lead.no_photos')}
              </div>
            {/if}
          </div>

          <div class="columns" style:grid-template-columns={panelWidth >= 640 ? 'minmax(0, 1.1fr) minmax(0, 1fr)' : 'minmax(0, 1fr)'}>
            <div class="card-box">
              <div class="mono-label card-head">{t('dashboard.lead.vehicle')}</div>
              {#each carFields as field (field.id)}
                {@const row = rowValue(field)}
                <div class="row">
                  <span class="key">{present.fieldLabel(field)}</span>
                  <span class="value" class:flag={row.flag} class:missing={row.missing} class:mono={!row.missing && (field.format === 'vin' || field.widget === 'year_grid' || field.unit === 'distance')}>
                    {#if row.flag}<span aria-hidden="true" class="flag-dot"></span>{/if}{row.text}
                  </span>
                </div>
              {/each}
            </div>

            <div class="card-box contact">
              <div class="mono-label card-head">{t('dashboard.lead.contact')}</div>
              <div class="contact-row stack">
                <span class="key">{t('dashboard.lead.name')}</span>
                <span class="name" class:missing={!name}>{purged ? t('dashboard.lead.purged', { days: dash.config.retentionDays }) : name || t('dashboard.lead.name_missing')}</span>
              </div>
              <div class="contact-row split">
                <span class="stack">
                  <span class="key">{t('dashboard.lead.phone')}</span>
                  <span class="phone" class:missing={!phone}>{purged ? t('dashboard.lead.purged', { days: dash.config.retentionDays }) : phone ? formatPhone(phone) : t('dashboard.lead.not_provided')}</span>
                </span>
                {#if phone}
                  <button class="copy" class:done={copied} aria-label={t('dashboard.lead.copy_aria')} onclick={copyPhone}>{copied ? t('dashboard.lead.copied') : t('dashboard.lead.copy')}</button>
                {/if}
              </div>
              {#if emailField}
                <div class="contact-row stack">
                  <span class="key">{t('dashboard.lead.email')}</span>
                  <span class="email" class:missing={!email}>{email || t('dashboard.lead.not_provided')}</span>
                </div>
              {/if}
              {#if methodField}
                <div class="contact-row split">
                  <span class="key">{t('dashboard.lead.preferred')}</span>
                  <span class="method">{present.display(methodField, lead.answers[methodField.id] ?? methodField.default)}</span>
                </div>
              {/if}
              {#if dash.desk && phone}
                <div class="actions">
                  <a class="call" href="tel:{phone}">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M5.2 2.5H3.4a1 1 0 00-1 1.1c.5 5.3 4.7 9.5 10 10a1 1 0 001.1-1v-1.8a1 1 0 00-.8-1l-2-.5a1 1 0 00-1 .3l-.8.8a8 8 0 01-3.5-3.5l.8-.8a1 1 0 00.3-1l-.5-2a1 1 0 00-1-.8z" style="stroke: var(--on-accent)" stroke-width="1.4" stroke-linejoin="round" /></svg>
                    {t('dashboard.lead.call_seller')}
                  </a>
                  {#if answer.key !== 'email'}
                    <a class="secondary" href={answer.href} {target} rel="noopener">{t(`dashboard.lead.${answer.key}`)}</a>
                  {/if}
                  {#if email}
                    <a class="secondary" href={mail}>
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="2" y="3.5" width="12" height="9" rx="1.5" stroke="#F4F3EE" stroke-width="1.4" /><path d="M2.5 4.5L8 8.5l5.5-4" stroke="#F4F3EE" stroke-width="1.4" stroke-linejoin="round" /></svg>
                      {t('dashboard.lead.email_seller')}
                    </a>
                  {/if}
                </div>
              {/if}
            </div>
          </div>

          <div class="section">
            <div class="section-head">
              <span class="mono-label">{t('dashboard.lead.notes')}</span>
              <span class="count">{lead.notes.length === 1 ? t('dashboard.lead.notes_count_one') : lead.notes.length ? t('dashboard.lead.notes_count', { count: lead.notes.length }) : ''}</span>
            </div>
            <div class="editor">
              <textarea
                bind:value={draft}
                rows="3"
                maxlength="1000"
                aria-label={t('dashboard.lead.note_aria')}
                placeholder={t('dashboard.lead.note_placeholder')}
                onkeydown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault()
                    void submitNote()
                  }
                }}
              ></textarea>
              <div class="editor-row">
                <span class="kbd-hint">{dash.desk ? t('dashboard.lead.note_hint') : ''}</span>
                <button class="add" class:ready={draft.trim()} disabled={!draft.trim()} onclick={submitNote}>{t('dashboard.lead.add_note')}</button>
              </div>
            </div>
            {#each lead.notes as note (note.id)}
              <div class="note">
                <div class="note-text">{note.text}</div>
                <div class="note-row">
                  <span class="note-when"><span class="lime-dot"></span>{dash.fmt.when(note.createdAt)}</span>
                  <button class="delete" aria-label={t('dashboard.lead.delete_note_aria')} onclick={() => dash.deleteNote(note.id)}>{t('dashboard.lead.delete_note')}</button>
                </div>
              </div>
            {/each}
          </div>

          <div class="activity">
            <span class="mono-label activity-head">{t('dashboard.lead.activity')}</span>
            {#each lead.events as event (event.id)}
              <div class="log status-{event.to}">
                <span class="status-dot"></span>
                <span class="log-text">{t('dashboard.lead.changed', { from: dash.statusLabel(event.from ?? ''), to: dash.statusLabel(event.to ?? '') })}</span>
                <span class="log-when">{dash.fmt.when(event.createdAt)}</span>
              </div>
            {/each}
            <div class="log received-row">
              <span class="status-dot gray"></span>
              <span class="log-text">{t('dashboard.lead.received_via', { source: lead.sourceLabel })}</span>
              <span class="log-when">{dash.fmt.when(lead.createdAt)}</span>
            </div>
          </div>
        </div>
      {/if}
    </div>

    {#if !dash.desk && phone}
      <div class="mobile-actions">
        <a class="call mobile" href="tel:{phone}">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M5.2 2.5H3.4a1 1 0 00-1 1.1c.5 5.3 4.7 9.5 10 10a1 1 0 001.1-1v-1.8a1 1 0 00-.8-1l-2-.5a1 1 0 00-1 .3l-.8.8a8 8 0 01-3.5-3.5l.8-.8a1 1 0 00.3-1l-.5-2a1 1 0 00-1-.8z" style="stroke: var(--on-accent)" stroke-width="1.4" stroke-linejoin="round" /></svg>
          {t('dashboard.lead.call')}
        </a>
        {#if answer.key !== 'email'}
          <a class="secondary mobile" href={answer.href} {target} rel="noopener">{t(`dashboard.lead.${answer.key}`)}</a>
        {/if}
        {#if email}
          <a class="secondary mobile" href={mail}>{t('dashboard.lead.email_short')}</a>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .overlay {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: flex;
    justify-content: flex-end;
  }

  .backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    animation: ui-fade 0.18s both;
  }

  .panel {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    border-left: 1px solid var(--line);
    animation: ui-panel 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both;
    padding-top: env(safe-area-inset-top);
  }

  .bar {
    flex: none;
    display: flex;
    align-items: center;
    gap: 8px;
    height: 60px;
    border-bottom: 1px solid #222424;
  }

  .icon-button {
    width: 44px;
    height: 44px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.12s;
  }

  .icon-button:hover {
    background: var(--surface);
  }

  .icon-button:active {
    transform: scale(0.92);
  }

  .id {
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .grow {
    flex: 1;
  }

  .pos {
    font: 500 12px/1 var(--font-mono);
    color: var(--text-faint);
    margin-right: 4px;
  }

  .step {
    width: 40px;
    height: 40px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .step:disabled {
    opacity: 0.35;
  }

  .step:hover:not(:disabled) {
    background: var(--surface);
  }

  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .content {
    display: flex;
    flex-direction: column;
    gap: 26px;
  }

  .top {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .chips {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 26px;
    padding: 0 10px;
    border-radius: 8px;
    background: var(--surface);
    border: 1px solid var(--line);
    font: 500 12px/1 var(--font-mono);
    color: var(--status-c);
  }

  .source {
    height: 26px;
    padding: 0 9px;
    border-radius: 8px;
    border: 1px solid #2e3030;
    font: 500 12px/24px var(--font-mono);
    color: var(--text-muted);
  }

  .received {
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .title-row {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px 24px;
    flex-wrap: wrap;
  }

  .title-block {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
  }

  h2 {
    margin: 0;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.045em;
    text-wrap: balance;
  }

  .sub {
    font: 500 14px/1 var(--font-mono);
    color: var(--text-soft);
  }

  .price-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .mono-label.small {
    font-size: 10.5px;
    color: var(--text-faint);
  }

  .price {
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    font-variant-numeric: tabular-nums;
  }

  .no-price {
    font: 500 17px/1.2 var(--font-sans);
    color: var(--text-muted);
  }

  .box {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .box-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .box-title {
    font: 600 14.5px/1.2 var(--font-sans);
  }

  .box-meta {
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .options {
    display: grid;
    gap: 6px;
  }

  .option {
    height: 46px;
    padding: 0 12px;
    border-radius: 11px;
    border: 1.5px solid var(--line);
    background: var(--surface-sunken);
    color: var(--text-muted);
    font: 600 14px/1 var(--font-sans);
    display: flex;
    align-items: center;
    gap: 9px;
    cursor: pointer;
    white-space: nowrap;
    transition:
      background-color 0.15s,
      border-color 0.15s,
      color 0.15s,
      transform 0.12s;
  }

  .option:hover {
    background: var(--surface-2);
    color: var(--text);
  }

  .option.on {
    background: var(--surface-2);
    border-color: var(--accent);
    color: var(--text);
  }

  .option:active {
    transform: scale(0.97);
  }

  .option-dot {
    width: 8px;
    height: 8px;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }

  .hint {
    font: 400 12.5px/1 var(--font-sans);
    color: var(--text-faint);
  }

  .count {
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .main-photo {
    position: relative;
    display: block;
    width: 100%;
    aspect-ratio: 16 / 9;
    padding: 0;
    border: 0;
    border-radius: 12px;
    overflow: hidden;
    background: var(--surface-2);
    cursor: zoom-in;
  }

  .main-photo:hover {
    filter: brightness(1.05);
  }

  .main-photo img,
  .thumb img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .tag {
    position: absolute;
    left: 10px;
    bottom: 10px;
    height: 24px;
    padding: 0 8px;
    border-radius: 7px;
    background: rgba(17, 18, 18, 0.86);
    border: 1px solid var(--line-strong);
    font: 500 11px/22px var(--font-mono);
    color: var(--text);
  }

  .thumbs {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 6px;
  }

  .thumb {
    position: relative;
    aspect-ratio: 4 / 3;
    padding: 0;
    border: 1px solid var(--line);
    border-radius: 9px;
    overflow: hidden;
    background: var(--surface-2);
    cursor: zoom-in;
    transition: border-color 0.15s;
  }

  .thumb:hover {
    border-color: var(--line-hover);
  }

  .thumb-num {
    position: absolute;
    left: 6px;
    bottom: 6px;
    font: 500 9.5px/1 var(--font-mono);
    color: var(--text);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  }

  .thumb-more {
    position: absolute;
    inset: 0;
    background: rgba(17, 18, 18, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    font: 600 16px/1 var(--font-sans);
    color: var(--text);
  }

  .no-photos {
    padding: 14px 16px;
    border-radius: 12px;
    border: 1px solid var(--line);
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  .columns {
    display: grid;
    gap: 12px;
    align-items: start;
  }

  .card-box {
    padding: 4px 16px 6px;
    border-radius: 14px;
    background: var(--surface);
    border: 1px solid var(--line);
  }

  .card-box.contact {
    display: flex;
    flex-direction: column;
    padding: 4px 16px 16px;
  }

  .card-head {
    padding: 14px 0 10px;
  }

  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    padding: 11px 0;
    border-top: 1px solid var(--line-soft);
  }

  .key {
    flex: none;
    font: 400 13.5px/1.3 var(--font-sans);
    color: var(--text-muted);
  }

  .value {
    display: flex;
    align-items: center;
    gap: 7px;
    font: 500 14.5px/1.3 var(--font-sans);
    text-align: right;
    overflow-wrap: anywhere;
  }

  .value.mono {
    font: 500 13.5px/1.3 var(--font-mono);
    letter-spacing: 0.02em;
  }

  .value.flag {
    color: var(--error-soft);
  }

  .value.missing {
    color: var(--text-faint);
  }

  .flag-dot {
    flex: none;
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--error);
  }

  .contact-row {
    padding: 12px 0;
    border-top: 1px solid var(--line-soft);
  }

  .stack {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .split {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
  }

  .name {
    font: 600 17px/1.3 var(--font-sans);
    letter-spacing: -0.01em;
  }

  .phone {
    font: 500 15px/1.3 var(--font-mono);
    letter-spacing: 0.02em;
  }

  .email {
    font: 500 15px/1.3 var(--font-sans);
    overflow-wrap: anywhere;
  }

  .method {
    font: 500 14.5px/1.3 var(--font-sans);
  }

  .missing {
    color: var(--text-faint);
  }

  .copy {
    flex: none;
    height: 34px;
    padding: 0 10px;
    border-radius: 9px;
    border: 1px solid #2e3030;
    background: transparent;
    color: var(--text);
    font: 500 12.5px/1 var(--font-sans);
    cursor: pointer;
  }

  .copy:hover {
    background: var(--surface-2);
  }

  .copy.done {
    color: var(--accent);
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 6px;
  }

  .call,
  .secondary {
    height: 48px;
    border-radius: 12px;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    transition: background-color 0.15s;
  }

  .call {
    background: var(--accent);
    color: var(--on-accent);
    font: 600 15.5px/1 var(--font-sans);
  }

  .call:hover {
    background: var(--accent-hover);
    color: var(--on-accent);
  }

  .secondary {
    height: 46px;
    border: 1px solid var(--line-strong);
    color: var(--text);
    font: 500 15px/1 var(--font-sans);
  }

  .secondary:hover {
    background: var(--surface-2);
    color: var(--text);
  }

  .editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px 12px 12px 14px;
    border-radius: 14px;
    background: var(--surface);
    border: 1.5px solid var(--line);
    transition:
      border-color 0.15s,
      box-shadow 0.15s;
  }

  .editor:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgb(var(--accent-rgb) / 0.18);
  }

  textarea {
    width: 100%;
    padding: 2px 0 0;
    border: 0;
    background: transparent;
    outline: none;
    resize: none;
    font: 400 15px/1.5 var(--font-sans);
    color: var(--text);
  }

  .editor-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .kbd-hint {
    font: 500 11px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .add {
    height: 38px;
    padding: 0 14px;
    border: 0;
    border-radius: 10px;
    background: var(--surface-2);
    color: var(--text-faint);
    font: 600 14px/1 var(--font-sans);
    cursor: pointer;
    transition:
      background-color 0.15s,
      color 0.15s,
      transform 0.12s;
  }

  .add.ready {
    background: var(--accent);
    color: var(--on-accent);
  }

  .add:active {
    transform: scale(0.96);
  }

  .note {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px 16px;
    border-radius: 12px;
    background: var(--surface-sunken);
    border: 1px solid var(--line);
    animation: ui-in 0.25s both;
  }

  .note-text {
    font: 400 14.5px/1.5 var(--font-sans);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .note-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .note-when {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .lime-dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--accent);
  }

  .delete {
    height: 30px;
    padding: 0 8px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--text-faint);
    font: 500 12.5px/1 var(--font-sans);
    cursor: pointer;
  }

  .delete:hover {
    color: var(--error);
    background: rgba(255, 138, 117, 0.08);
  }

  .activity {
    display: flex;
    flex-direction: column;
  }

  .activity-head {
    margin-bottom: 10px;
  }

  .log {
    display: grid;
    grid-template-columns: 14px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: baseline;
    padding: 11px 0;
    border-top: 1px solid #222424;
  }

  .status-dot.gray {
    background: #3a3c3c;
    box-shadow: inset 0 0 0 1.5px #3a3c3c;
  }

  .log-text {
    font: 400 14px/1.4 var(--font-sans);
    color: var(--text-soft);
  }

  .log-when {
    font: 500 11.5px/1 var(--font-mono);
    color: var(--text-faint);
    white-space: nowrap;
  }

  .mobile-actions {
    flex: none;
    display: flex;
    gap: 8px;
    padding: 12px 16px max(10px, env(safe-area-inset-bottom));
    border-top: 1px solid #222424;
    background: var(--bg);
  }

  .mobile {
    flex: 1;
    height: 52px;
    border-radius: 14px;
    font: 600 16px/1 var(--font-sans);
  }

  .secondary.mobile {
    background: var(--surface);
  }
</style>
