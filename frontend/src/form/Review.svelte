<script lang="ts">
  // Review: every answered section with an Edit link, then the photos.
  // Sections follow the preset's step groups.
  import { getContext } from 'svelte'
  import type { FieldSpec, Step } from '../shared/config'
  import { activeSteps, isEmpty, isStepBlank, visibleFields } from './engine'
  import type { FormState } from './state.svelte'
  import StepTitle from './StepTitle.svelte'

  const form = getContext<FormState>('form')
  const t = form.t

  interface Row {
    key: string
    value: string
  }

  function rowFor(step: Step, field: FieldSpec): Row | null {
    const value = form.answers[field.id] ?? field.default
    const label = form.fieldLabel(field, 'review')
    if (!isEmpty(value)) {
      let text = form.display(field, value)
      // Follow-up details go next to the answer that unlocked them: "Yes · Dent".
      for (const child of field.follow_up && value === field.follow_up.when ? field.follow_up.fields : []) {
        const extra = form.answers[child.id]
        if (!isEmpty(extra)) text += ` · ${String(extra).trim()}`
      }
      return { key: label, value: text }
    }
    const empty = t(`preset.fields.${field.id}.review_empty`)
    if (!empty.startsWith('preset.')) return { key: label, value: empty }
    const skipped = step.skippable && isStepBlank(step, form.answers)
    return field.required && !skipped ? { key: label, value: t('form.review.not_provided') } : null
  }

  const groups = $derived.by(() => {
    const result: { id: string; title: string; editTo: string; rows: Row[] }[] = []
    const steps = activeSteps(form.preset)
    for (const step of steps.slice(0, steps.indexOf(steps.find((s) => s.submit)!) + 1)) {
      const id = step.group ?? step.id
      let group = result.find((g) => g.id === id)
      if (!group) {
        const title = t(`preset.groups.${id}`)
        group = { id, title: title.startsWith('preset.') ? t(`preset.steps.${step.id}.tag`) : title, editTo: step.id, rows: [] }
        result.push(group)
      }
      for (const field of visibleFields(step, form.answers)) {
        if (field.type === 'photos' || form.preset.steps.some((s) => s.fields.some((f) => f.follow_up?.fields.includes(field)))) continue
        const row = rowFor(step, field)
        if (row) group.rows.push(row)
      }
    }
    return result.filter((group) => group.rows.length)
  })

  const photos = $derived(form.donePhotos)
  const photoStep = $derived(activeSteps(form.preset).find((s) => s.fields.some((f) => f.type === 'photos')))
</script>

<StepTitle tag={t('form.review.tag')} title={t('form.review.title')} hint={t('form.review.hint')} />

{#if form.submitFailed}
  <div role="alert" class="banner">
    <span aria-hidden="true" class="badge">!</span>
    <span class="banner-text">
      <span class="banner-title">{t('form.review.failed_title')}</span>
      <span class="banner-body">{t(form.limited ? 'form.review.limited_text' : 'form.review.failed_text', { id: form.leadId ?? '' })}</span>
    </span>
  </div>
{/if}

{#each groups as group (group.id)}
  <div data-st class="card">
    <div class="head">
      <span class="title">{group.title}</span>
      <button class="edit" disabled={form.busy} aria-label={t('form.review.edit_aria', { section: form.present.lower(group.title) })} onclick={() => form.edit(group.editTo)}>
        {t('form.review.edit')}
      </button>
    </div>
    {#each group.rows as row (row.key)}
      <div class="row"><span class="key">{row.key}</span><span class="value">{row.value}</span></div>
    {/each}
  </div>
{/each}

{#if photoStep}
  <div data-st class="card photos">
    <div class="head">
      <span class="title photos-title">{t('form.review.photos_head', { count: photos.length })}</span>
      <button class="edit" disabled={form.busy} aria-label={t('form.review.edit_photos_aria')} onclick={() => form.edit(photoStep.id)}>
        {t('form.review.edit')}
      </button>
    </div>
    {#if photos.length}
      <div class="thumbs">
        {#each photos as photo, index (index)}
          <span class="thumb"><img src={photo.url} alt="" /></span>
        {/each}
      </div>
    {:else}
      <span class="none">{t('form.review.no_photos')}</span>
    {/if}
  </div>
{/if}

<style>
  .banner {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    padding: 14px 16px;
    border-radius: 16px;
    background: rgba(255, 138, 117, 0.08);
    border: 1px solid rgba(255, 138, 117, 0.35);
    margin-bottom: 12px;
    animation: ui-in 0.25s both;
  }

  .badge {
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

  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 4px 6px 4px 18px;
    margin-bottom: 8px;
  }

  .card.photos {
    padding: 4px 6px 14px 18px;
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    font: 500 11px/1 var(--font-mono);
    color: var(--text-muted);
    padding: 14px 0 6px;
  }

  .photos-title {
    padding: 14px 0 10px;
  }

  .edit {
    height: 44px;
    padding: 0 12px;
    border: 0;
    border-radius: 10px;
    background: transparent;
    font: 500 13.5px/1 var(--font-sans);
    color: var(--accent);
    cursor: pointer;
  }

  .edit:hover {
    background: var(--surface-2);
  }

  .row {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    padding: 10px 12px 10px 0;
    border-top: 1px solid var(--line-soft);
  }

  .key {
    flex: none;
    font: 400 13.5px/1.35 var(--font-sans);
    color: var(--text-muted);
  }

  .value {
    font: 500 14.5px/1.35 var(--font-sans);
    text-align: right;
    overflow-wrap: anywhere;
  }

  .thumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding-right: 12px;
  }

  .thumb {
    position: relative;
    width: 50px;
    height: 50px;
    border-radius: 10px;
    overflow: hidden;
    background: repeating-linear-gradient(135deg, #2c2e2e 0 6px, #262828 6px 12px);
    border: 1px solid var(--line-strong);
  }

  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .none {
    font: 400 14px/1.4 var(--font-sans);
    color: var(--text-muted);
  }
</style>
