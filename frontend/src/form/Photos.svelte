<script lang="ts">
  // Photo step: one tile per guided angle with its illustration, plus extra
  // photos. Each photo uploads as soon as it is picked.
  import { getContext } from 'svelte'
  import type { PhotoSlot } from '../shared/config'
  import ErrorText from './ErrorText.svelte'
  import { illustration } from './illustrations'
  import type { FormState, PhotoItem } from './state.svelte'
  import StepTitle from './StepTitle.svelte'

  let { scroller: _scroller }: { scroller?: HTMLElement } = $props()
  const form = getContext<FormState>('form')
  const t = form.t
  const field = form.photosField!

  let libraryInput: HTMLInputElement | undefined = $state()
  let moreInput: HTMLInputElement | undefined = $state()
  let pendingSlot: string | null = null

  const extras = $derived(Object.entries(form.photos).filter(([, photo]) => photo.slot === null))
  const added = $derived(field.slots.filter((slot) => form.photos[slot.id]?.status === 'done').length)
  const extraDone = $derived(extras.filter(([, photo]) => photo.status === 'done').length)
  const summary = $derived.by(() => {
    const base = t('form.photos.summary', { added, total: field.slots.length })
    return extraDone ? t('form.photos.summary_more', { summary: base, count: extraDone }) : base
  })
  const pad2 = (n: number) => String(n).padStart(2, '0')

  function pick(slot: string) {
    pendingSlot = slot
    libraryInput?.click()
  }

  function onFiles(event: Event & { currentTarget: HTMLInputElement }, slot: string | null) {
    const files = Array.from(event.currentTarget.files ?? [])
    event.currentTarget.value = ''
    void form.addPhotos(slot, files)
  }

  function photoError(photo: PhotoItem): string {
    return photo.error ? t(`form.photos.errors.${photo.error}`, photo.errorParams ?? {}) : ''
  }

  function action(photo: PhotoItem | undefined): string {
    if (!photo) return t('form.photos.add')
    if (photo.status === 'error') return t('form.photos.retry')
    if (photo.status === 'uploading') return t('form.photos.change')
    return t('form.photos.replace')
  }

  function stateOf(photo: PhotoItem | undefined): 'empty' | PhotoItem['status'] {
    return photo?.status ?? 'empty'
  }

  function tileLabel(slot: PhotoSlot) {
    return t(`preset.photos.${slot.id}.label`)
  }
</script>

<StepTitle tag={t('preset.steps.photos.tag')} title={t('preset.steps.photos.title')} hint={t('preset.steps.photos.hint')} />

<div data-st class="top">
  <span class="summary">{summary}</span>
  <span class="saved"><span class="saved-dot"></span>{form.leadId ? t('form.photos.saved') : t('form.photos.not_saved')}</span>
</div>

<div class="grid">
  {#each field.slots as slot, index (slot.id)}
    {@const photo = form.photos[slot.id]}
    {@const state = stateOf(photo)}
    {@const label = tileLabel(slot)}
    {@const guide = illustration(slot.image)}
    <div data-st class="tile" class:done={state === 'done'} class:failed={state === 'error'}>
      <button
        class="area"
        class:blank={state === 'empty' || state === 'error'}
        style:aspect-ratio={slot.ratio}
        aria-label={photo ? t('form.photos.aria_replace', { label: form.present.lower(label) }) : t('form.photos.aria_add', { label: form.present.lower(label) })}
        onclick={() => pick(slot.id)}
      >
        {#if (state === 'empty' || state === 'error') && guide}
          <img src={guide} alt="" aria-hidden="true" draggable="false" class="guide" class:dim={state === 'error'} />
        {/if}
        {#if state === 'empty'}
          <span aria-hidden="true" class="plus">
            <svg width="10" height="10" viewBox="0 0 12 12"><path d="M6 1.5v9M1.5 6h9" style="stroke: var(--accent)" stroke-width="1.8" stroke-linecap="round" /></svg>
          </span>
        {/if}
        {#if photo && state !== 'error' && photo.url}
          <img src={photo.url} alt={t('form.photos.photo_alt', { label })} class="shot" />
        {/if}
        {#if state === 'uploading'}
          <span class="progress">
            <span class="progress-row"><span>{t('form.photos.uploading')}</span><span>{Math.round((photo?.progress ?? 0) * 100)}%</span></span>
            <span class="track"><span class="track-fill" style:width="{(photo?.progress ?? 0) * 100}%"></span></span>
          </span>
        {/if}
        {#if state === 'error'}
          <span class="failure"><span aria-hidden="true" class="failure-badge">!</span><span>{photoError(photo!)}</span></span>
        {/if}
      </button>
      {#if photo}
        <button
          class="remove"
          aria-label={t('form.photos.aria_remove', { label: form.present.lower(label) })}
          onclick={(event) => {
            event.stopPropagation()
            void form.removePhoto(slot.id)
          }}
        >
          <span class="remove-box"><svg width="10" height="10" viewBox="0 0 10 10"><path d="M2 2l6 6M8 2L2 8" stroke="#F4F3EE" stroke-width="1.5" stroke-linecap="round" /></svg></span>
        </button>
      {/if}
      <div class="footer">
        <span class="num" class:lit={state === 'done'}>{pad2(index + 1)}</span>
        <span class="tile-label">{label}</span>
        {#if photo}
          <button class="tile-action" class:empty={!photo} tabindex="-1" onclick={() => pick(slot.id)}>{action(photo)}</button>
        {/if}
      </div>
    </div>
  {/each}

  <div data-st class="more">
    <button class="more-button" style:min-height={extras.length ? '0px' : '150px'} aria-label={t('form.photos.add_more_aria')} onclick={() => moreInput?.click()}>
      <span aria-hidden="true" class="more-ring">
        <svg width="18" height="18" viewBox="0 0 18 18"><path d="M9 2.5v13M2.5 9h13" style="stroke: var(--accent)" stroke-width="1.8" stroke-linecap="round" /></svg>
      </span>
      <span class="more-text">
        <span class="more-title">{t('form.photos.add_more_title')}</span>
        <span class="more-sub">{t('form.photos.add_more_text')}</span>
      </span>
    </button>
    {#if extras.length}
      <div class="extras">
        {#each extras as [key, photo], index (key)}
          <div class="extra" class:failed={photo.status === 'error'}>
            {#if photo.url && photo.status !== 'error'}
              <img src={photo.url} alt={t('form.photos.extra_alt', { n: index + 1 })} />
            {/if}
            {#if photo.status === 'uploading'}
              <span class="extra-track"><span class="track-fill" style:width="{photo.progress * 100}%"></span></span>
            {/if}
            {#if photo.status === 'error'}
              <span class="extra-error">{photoError(photo)}</span>
            {/if}
            <button class="remove extra-remove" aria-label={t('form.photos.extra_remove', { n: index + 1 })} onclick={() => form.removePhoto(key)}>
              <span class="remove-box small"><svg width="10" height="10" viewBox="0 0 10 10"><path d="M2 2l6 6M8 2L2 8" stroke="#F4F3EE" stroke-width="1.5" stroke-linecap="round" /></svg></span>
            </button>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</div>

{#if form.errors.photos}
  <ErrorText text={t(`form.photos.errors.${form.errors.photos.code}`, form.errors.photos.params ?? {})} gap="12px" />
{/if}
<div data-st class="footnote">{t('form.photos.footnote')}</div>

<input bind:this={libraryInput} type="file" accept="image/*,.heic,.heif" tabindex="-1" aria-hidden="true" class="hidden" onchange={(event) => onFiles(event, pendingSlot)} />
<input bind:this={moreInput} type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" multiple tabindex="-1" aria-hidden="true" class="hidden" onchange={(event) => onFiles(event, null)} />

<style>
  .top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .summary {
    font: 500 14px/1.3 var(--font-sans);
  }

  .saved {
    display: flex;
    align-items: center;
    gap: 6px;
    font: 500 11px/1 var(--font-mono);
    color: var(--text-muted);
  }

  .saved-dot {
    width: 6px;
    height: 6px;
    border-radius: 3px;
    background: var(--accent);
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .tile {
    position: relative;
    display: flex;
    flex-direction: column;
    border-radius: 18px;
    overflow: hidden;
    border: 1.5px solid var(--line);
    background: var(--surface);
    transition: border-color 0.2s;
  }

  .tile.done {
    border-color: #3a3c3c;
  }

  .tile.failed {
    border-color: rgba(255, 138, 117, 0.55);
  }

  .area {
    position: relative;
    display: block;
    width: 100%;
    padding: 0;
    border: 0;
    background: var(--surface);
    cursor: pointer;
    overflow: hidden;
    transition: filter 0.2s;
  }

  .area.blank {
    background: var(--surface-sunken);
  }

  .area:hover {
    filter: brightness(1.04);
  }

  .guide {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: contain;
    transition: opacity 0.2s;
  }

  .guide.dim {
    opacity: 0.35;
  }

  .plus {
    position: absolute;
    right: 8px;
    bottom: 8px;
    width: 26px;
    height: 26px;
    border-radius: 13px;
    background: rgba(17, 18, 18, 0.82);
    border: 1.5px solid var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .shot {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    animation: ui-reveal 0.45s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .progress {
    position: absolute;
    left: 8px;
    right: 8px;
    bottom: 8px;
    display: flex;
    flex-direction: column;
    gap: 7px;
    padding: 9px 10px;
    border-radius: 11px;
    background: rgba(17, 18, 18, 0.88);
    border: 1px solid var(--line-strong);
  }

  .progress-row {
    display: flex;
    justify-content: space-between;
    font: 500 11px/1 var(--font-mono);
    color: var(--text);
  }

  .track {
    position: relative;
    display: block;
    height: 3px;
    border-radius: 2px;
    background: var(--line-strong);
    overflow: hidden;
  }

  .track-fill {
    display: block;
    height: 100%;
    background: var(--accent);
    transition: width 0.2s linear;
  }

  .failure {
    position: absolute;
    left: 8px;
    right: 8px;
    bottom: 8px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    padding: 9px 10px;
    border-radius: 11px;
    background: rgba(17, 18, 18, 0.92);
    border: 1px solid rgba(255, 138, 117, 0.4);
    text-align: left;
    font: 500 12px/1.3 var(--font-sans);
    color: var(--error-soft);
  }

  .failure-badge {
    flex: none;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    background: var(--error);
    color: #111212;
    font: 700 10px/14px var(--font-sans);
    text-align: center;
  }

  .remove {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 44px;
    height: 44px;
    border: 0;
    background: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.12s;
  }

  .remove:active {
    transform: scale(0.9);
  }

  .remove-box {
    width: 28px;
    height: 28px;
    border-radius: 9px;
    background: rgba(17, 18, 18, 0.85);
    border: 1px solid var(--line-strong);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .remove-box.small {
    width: 26px;
    height: 26px;
    border-radius: 8px;
  }

  .footer {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 6px 8px 12px;
    border-top: 1px solid var(--line);
    min-height: 52px;
  }

  .num {
    font: 500 10.5px/1 var(--font-mono);
    color: var(--text-faint);
  }

  .num.lit {
    color: var(--accent);
  }

  .tile-label {
    flex: 1;
    min-width: 0;
    font: 600 13.5px/1.2 var(--font-sans);
    text-wrap: balance;
  }

  .tile-action {
    flex: none;
    height: 36px;
    padding: 0 10px;
    border-radius: 10px;
    border: 1px solid var(--line-strong);
    background: transparent;
    color: var(--text);
    font: 600 12.5px/1 var(--font-sans);
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    transition: transform 0.12s;
  }

  .tile-action:active {
    transform: scale(0.94);
  }

  .more {
    grid-column: span 2;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .more-button {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    width: 100%;
    padding: 22px 20px;
    border-radius: 18px;
    border: 1.5px dashed var(--line-strong);
    background: var(--surface-sunken);
    color: var(--text);
    cursor: pointer;
    text-align: center;
    transition:
      border-color 0.2s,
      background-color 0.2s,
      transform 0.12s;
  }

  .more-button:hover {
    border-color: var(--line-hover);
    background: var(--surface);
  }

  .more-button:active {
    transform: scale(0.99);
  }

  .more-ring {
    width: 48px;
    height: 48px;
    border-radius: 24px;
    border: 1.5px solid var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .more-text {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .more-title {
    font: 600 13px/1.2 var(--font-sans);
    letter-spacing: 0.1em;
  }

  .more-sub {
    font: 400 13.5px/1.4 var(--font-sans);
    color: var(--text-muted);
  }

  .extras {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .extra {
    position: relative;
    aspect-ratio: 1 / 1;
    border-radius: 14px;
    overflow: hidden;
    background: var(--surface);
    border: 1.5px solid var(--line);
    animation: ui-reveal 0.35s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .extra.failed {
    border-color: rgba(255, 138, 117, 0.55);
  }

  .extra img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .extra-track {
    position: absolute;
    left: 6px;
    right: 6px;
    bottom: 6px;
    height: 3px;
    border-radius: 2px;
    background: rgba(17, 18, 18, 0.7);
    overflow: hidden;
  }

  .extra-error {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: flex-end;
    padding: 8px;
    background: rgba(17, 18, 18, 0.88);
    font: 500 11px/1.3 var(--font-sans);
    color: var(--error-soft);
  }

  .extra-remove {
    top: 0;
    right: 0;
  }

  .footnote {
    margin-top: 14px;
    font: 400 13px/1.45 var(--font-sans);
    color: var(--text-muted);
    text-wrap: pretty;
  }

  .hidden {
    display: none;
  }
</style>
