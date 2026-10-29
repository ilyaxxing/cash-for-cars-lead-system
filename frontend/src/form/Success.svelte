<script lang="ts">
  // Done: a summary of the car with its photos and what happens next.
  import { getContext } from 'svelte'
  import type { FieldSpec } from '../shared/config'
  import { formatPhone } from '../shared/region'
  import type { FormState } from './state.svelte'

  const form = getContext<FormState>('form')
  const t = form.t

  const fields = form.preset.steps.flatMap((step) => step.fields)
  const field = (id: string): FieldSpec | undefined => fields.find((f) => f.id === id)
  const answer = (id: string) => form.answers[id]
  const shown = (id: string) => {
    const spec = field(id)
    return spec ? form.display(spec, answer(id)) : ''
  }

  const photos = form.donePhotos
  const thumbs = photos.slice(1, 4)
  const more = photos.length - 4
  const corners = ['4px 4px 4px 19px', '4px', '4px 4px 19px 4px']
  const carName = [answer('make'), answer('model')].filter(Boolean).join(' ')
  const sub = [shown('year'), shown('mileage')].filter(Boolean).join(' · ')

  // Condition-like summary: the first option field drawn with a level meter.
  const levelField = fields.find((f) => f.type === 'select' && f.options.some((o) => o.level !== undefined))
  const vinField = fields.find((f) => f.format === 'vin')
  const rows = [
    levelField && { key: form.fieldLabel(levelField), value: shown(levelField.id), mono: false },
    photos.length && {
      key: t('form.success.photos'),
      value: photos.length === 1 ? t('form.success.photos_count_one') : t('form.success.photos_count', { count: photos.length }),
      mono: false,
    },
    vinField && answer(vinField.id) && { key: form.fieldLabel(vinField), value: String(answer(vinField.id)), mono: true },
  ].filter((row): row is { key: string; value: string; mono: boolean } => Boolean(row && row.value))

  const method = String(answer('contact_method') ?? field('contact_method')?.default ?? 'call')
  const methodBy = t(`preset.options.contact_method.${method}.by`)
  // The number as the review showed it, not as it was typed.
  const contact = method === 'email' ? String(answer('email') ?? '') : formatPhone(String(answer('phone') ?? ''))
  const next = [
    { n: '1', title: t('form.success.next1_title'), text: t('form.success.next1_text'), lit: true },
    {
      n: '2',
      title: t('form.success.next2_title', { method: methodBy.startsWith('preset.') ? method : methodBy }),
      text: t('form.success.next2_text', { contact: contact || t('form.success.next2_fallback') }),
      lit: false,
    },
    { n: '3', title: t('form.success.next3_title'), text: t('form.success.next3_text'), lit: false },
  ]

  // Back to the start. Not window.close(): iPhone Safari closes a tab opened
  // from a QR code, and the seller lands on whatever tab was behind it.
  const done = () => form.restart()
</script>

<div class="success" style:padding-top={form.wide ? '4vh' : '14px'}>
  <div class="mark">
    <span class="ring"></span>
    <span class="fill">
      <svg width="34" height="34" viewBox="0 0 36 36" aria-hidden="true">
        <path class="draw" d="M9.5 18.5l5.8 5.8L27 12.5" style="stroke: var(--on-accent)" stroke-width="3.2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </span>
  </div>
  <div role="status" class="status"><span class="dot"></span>{t('form.success.status')}</div>
  <h1 style:font-size={form.wide ? '72px' : '48px'}>{t('form.success.title')}</h1>
  <p class="lead">{t('form.success.text')}</p>

  <div class="car">
    {#if photos.length}
      <div class="collage">
        <div class="main" style:border-radius={thumbs.length ? '19px 19px 4px 4px' : '19px'}>
          <img src={photos[0].url} alt={carName} />
        </div>
        {#if thumbs.length}
          <div class="thumbs" style:grid-template-columns="repeat({thumbs.length}, minmax(0, 1fr))">
            {#each thumbs as photo, index (index)}
              {@const radius = thumbs.length === 1 ? '4px 4px 19px 19px' : index === 0 ? corners[0] : index === thumbs.length - 1 ? corners[2] : corners[1]}
              <div class="thumb" style:border-radius={radius}>
                <img src={photo.url} alt="" />
                {#if index === thumbs.length - 1 && more > 0}
                  <span class="more" aria-label={t('form.success.more_photos', { count: more })}>+{more}</span>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
    <div class="body" style:padding={photos.length ? '18px 20px 6px' : '20px 20px 6px'}>
      {#if !photos.length}<span class="your-car">{t('form.success.your_car')}</span>{/if}
      <div class="name">{carName || t('form.success.your_car')}</div>
      {#if sub}<div class="sub">{sub}</div>{/if}
      <div class="rows">
        {#each rows as row (row.key)}
          <div class="row"><span class="key">{row.key}</span><span class="value" class:mono={row.mono}>{row.value}</span></div>
        {/each}
      </div>
    </div>
  </div>

  <div class="next-title">{t('form.success.next_title')}</div>
  <div class="next">
    {#each next as item (item.n)}
      <div class="next-item">
        <span class="next-n" class:lit={item.lit}>{item.n}</span>
        <span class="next-text"><span class="next-head">{item.title}</span><span class="next-body">{item.text}</span></span>
      </div>
    {/each}
  </div>

  <div class="actions">
    <button class="done" onclick={done}>{t('form.success.done')}</button>
    <button class="again" onclick={form.restart}>{t('form.success.another')}</button>
  </div>
</div>

<style>
  .success {
    display: flex;
    flex-direction: column;
  }

  .mark {
    position: relative;
    width: 72px;
    height: 72px;
    margin-bottom: 26px;
  }

  .ring {
    position: absolute;
    inset: 0;
    border-radius: 24px;
    border: 1.5px solid var(--accent);
    animation: ui-ring 0.9s 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .fill {
    position: absolute;
    inset: 0;
    border-radius: 24px;
    background: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    animation: ui-pop 0.3s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .draw {
    stroke-dasharray: 32;
    stroke-dashoffset: 32;
    animation: ui-draw 0.3s 0.2s cubic-bezier(0.65, 0, 0.35, 1) forwards;
  }

  .status {
    display: flex;
    align-items: center;
    gap: 8px;
    font: 500 12px/1 var(--font-mono);
    color: var(--text-muted);
    margin-bottom: 14px;
    animation: ui-in 0.3s 0.25s both;
  }

  .dot {
    width: 6px;
    height: 6px;
    border-radius: 2px;
    background: var(--accent);
  }

  h1 {
    margin: 0 0 12px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    animation: ui-in 0.3s 0.3s both;
  }

  .lead {
    margin: 0 0 26px;
    font: 400 16px/1.5 var(--font-sans);
    color: var(--text-soft);
    text-wrap: pretty;
    animation: ui-in 0.3s 0.36s both;
  }

  .car {
    border-radius: 22px;
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--line);
    margin-bottom: 24px;
    animation: ui-in 0.3s 0.42s both;
  }

  .collage {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding: 3px;
  }

  .main {
    position: relative;
    aspect-ratio: 16 / 10;
    overflow: hidden;
    background: var(--surface-2);
  }

  .thumbs {
    display: grid;
    gap: 3px;
  }

  .thumb {
    position: relative;
    aspect-ratio: 4 / 3;
    overflow: hidden;
    background: var(--surface-2);
  }

  .main img,
  .thumb img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .more {
    position: absolute;
    inset: 0;
    background: rgba(17, 18, 18, 0.66);
    display: flex;
    align-items: center;
    justify-content: center;
    font: 600 19px/1 var(--font-sans);
    letter-spacing: -0.02em;
    color: var(--text);
  }

  .body {
    display: flex;
    flex-direction: column;
  }

  .your-car {
    margin-bottom: 12px;
    font: 500 11px/1 var(--font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-faint);
  }

  .name {
    font: 700 26px/1.1 var(--font-sans);
    letter-spacing: -0.03em;
    text-wrap: balance;
  }

  .sub {
    margin-top: 7px;
    font: 500 15px/1.3 var(--font-sans);
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  .rows {
    margin-top: 16px;
    display: flex;
    flex-direction: column;
  }

  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 14px;
    padding: 12px 0;
    border-top: 1px solid var(--line-soft);
  }

  .key {
    flex: none;
    font: 400 13.5px/1.3 var(--font-sans);
    color: var(--text-muted);
  }

  .value {
    font: 500 14.5px/1.3 var(--font-sans);
    text-align: right;
  }

  .value.mono {
    font: 500 13px/1.3 var(--font-mono);
    letter-spacing: 0.04em;
    overflow-wrap: anywhere;
  }

  .next-title {
    font: 500 11px/1 var(--font-mono);
    color: var(--text-muted);
    margin-bottom: 4px;
    animation: ui-in 0.3s 0.48s both;
  }

  .next {
    display: flex;
    flex-direction: column;
    margin-bottom: 28px;
    animation: ui-in 0.3s 0.52s both;
  }

  .next-item {
    display: flex;
    gap: 14px;
    padding: 14px 0;
    border-bottom: 1px solid var(--line-soft);
  }

  .next-n {
    flex: none;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: var(--surface-2);
    color: var(--text);
    font: 500 11px/24px var(--font-mono);
    text-align: center;
  }

  .next-n.lit {
    background: var(--accent);
    color: var(--on-accent);
  }

  .next-text {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .next-head {
    font: 600 15.5px/1.3 var(--font-sans);
  }

  .next-body {
    font: 400 14px/1.45 var(--font-sans);
    color: var(--text-muted);
  }

  .actions {
    display: flex;
    flex-direction: column;
    gap: 10px;
    animation: ui-in 0.3s 0.58s both;
  }

  .done {
    height: 58px;
    border: 0;
    border-radius: 16px;
    background: var(--accent);
    color: var(--on-accent);
    font: 600 17px/1 var(--font-sans);
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .done:hover {
    background: var(--accent-hover);
  }

  .done:active,
  .again:active {
    transform: scale(0.98);
  }

  .again {
    height: 54px;
    border: 1px solid var(--line-strong);
    border-radius: 16px;
    background: transparent;
    color: var(--text);
    font: 500 16px/1 var(--font-sans);
    cursor: pointer;
    transition:
      background-color 0.15s,
      transform 0.12s;
  }

  .again:hover {
    background: var(--surface);
  }
</style>
