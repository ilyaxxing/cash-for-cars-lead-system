<script lang="ts">
  import { getContext } from 'svelte'
  import * as api from './api'
  import { placementQR } from './placement-qr'
  import type { DashboardState } from './state.svelte'

  const dash = getContext<DashboardState>('dashboard')
  const t = dash.t
  let mode = $state<'closed' | 'list' | 'add'>('closed')
  let sources = $state<api.Placement[]>([])
  let selected = $state('')
  const current = $derived(sources.find((source) => source.code === selected))
  let name = $state('')
  let busy = $state(false)
  let message = $state('')
  let copied = $state(false)
  let assets = $state<Awaited<ReturnType<typeof placementQR>> | null>(null)

  function failed(error: unknown) {
    if (error instanceof api.Unauthorized) dash.auth = 'signed_out'
    message = t(error instanceof api.RequestFailed && error.code === 'public_domain_required'
      ? 'dashboard.qr.domain' : 'dashboard.qr.failed')
  }

  async function open(next: 'list' | 'add') {
    mode = mode === next ? 'closed' : next
    message = ''
    if (mode === 'closed') return
    busy = true
    try {
      sources = await api.getSources()
      if (!sources.some((source) => source.code === selected)) selected = sources[0]?.code ?? ''
    } catch (error) {
      failed(error)
    } finally {
      busy = false
    }
  }

  async function create(event: SubmitEvent) {
    event.preventDefault()
    if (!name.trim() || busy) return
    busy = true
    message = ''
    try {
      const source = await api.createSource(name.trim())
      sources = [source, ...sources.filter((item) => item.code !== source.code)]
      selected = source.code
      name = ''
      mode = 'list'
    } catch (error) {
      failed(error)
    } finally {
      busy = false
    }
  }

  $effect(() => {
    const source = current
    copied = false
    assets = null
    if (!source || mode !== 'list') return
    let active = true
    let images: Awaited<ReturnType<typeof placementQR>> | null = null
    const release = () => {
      if (images) {
        URL.revokeObjectURL(images.png)
        URL.revokeObjectURL(images.svg)
      }
    }
    placementQR(source.url, source.code).then((result) => {
      images = result
      if (active) assets = result
      else release()
    }).catch((error) => { if (active) failed(error) })
    return () => { active = false; release() }
  })

  async function share(event: MouseEvent) {
    if (!assets || !navigator.canShare?.({ files: [assets.file] })) return
    const { file, png } = assets
    event.preventDefault()
    try {
      await navigator.share({ files: [file] })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      const fallback = document.createElement('a')
      fallback.href = png
      fallback.download = file.name
      fallback.click()
    }
  }

  let linkInput = $state<HTMLInputElement>()
  async function copy() {
    if (!current) return
    try {
      await navigator.clipboard.writeText(current.url)
      copied = true
    } catch {
      linkInput?.focus()
      linkInput?.select()
    }
  }
</script>

<div class="manager">
  <div class="buttons">
    <button class="accent" disabled={busy} aria-expanded={mode === 'add'} onclick={() => open('add')}>{t('dashboard.qr.add')}</button>
    <button disabled={busy} aria-expanded={mode === 'list'} onclick={() => open('list')}>{t('dashboard.qr.codes')}</button>
  </div>
  {#if mode === 'add'}
    <form onsubmit={create}>
      <label>{t('dashboard.qr.name')}<input bind:value={name} maxlength="80" required /></label>
      <button disabled={!name.trim() || busy}>{t('dashboard.qr.create')}</button>
    </form>
  {:else if mode === 'list' && sources.length}
    <div class="detail">
      <label>{t('dashboard.qr.source')}
        <select bind:value={selected} onchange={() => message = ''}>
          {#each sources as source (source.code)}<option value={source.code}>{source.name}</option>{/each}
        </select>
      </label>
      {#if current}
        {#if assets}<img src={assets.png} alt={t('dashboard.qr.codes') + ' · ' + current.name} width="172" height="172" />{/if}
        <label>{t('dashboard.qr.link')}<input bind:this={linkInput} readonly value={current.url} /></label>
        <div class="buttons">
          {#if assets}
            <a class="accent" href={assets.png} download={assets.file.name} onclick={share}>{t('dashboard.qr.save')}</a>
            <a href={assets.svg} download={'qr-' + current.code + '.svg'}>{t('dashboard.qr.print')}</a>
          {/if}
          <button onclick={copy}>{copied ? t('dashboard.lead.copied') : t('dashboard.qr.copy')}</button>
        </div>
      {/if}
    </div>
  {/if}
  {#if message}<p role="alert">{message}</p>{/if}
</div>

<style>
  .manager { margin: 0 0 12px; }
  .buttons { display: flex; gap: 8px; flex-wrap: wrap; }
  form, .detail { display: grid; gap: 12px; margin-top: 14px; }
  label { display: grid; gap: 6px; min-width: 0; font-size: 13px; color: var(--text-muted); }
  input, select, button, a { box-sizing: border-box; min-height: 44px; border-radius: 10px; font: inherit; color: var(--text); border: 1px solid var(--line); background: var(--surface-2); }
  input, select { padding: 8px 10px; width: 100%; font-size: 16px; }
  button, a { display: inline-flex; align-items: center; justify-content: center; padding: 9px 13px; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
  form button { justify-self: start; }
  .accent { background: var(--accent); color: var(--on-accent); }
  button:disabled { opacity: .55; }
  img { max-width: 100%; height: auto; image-rendering: pixelated; }
  p { color: var(--text); font-size: 14px; }
</style>
