// State and transitions of the seller form, shared by its components.
//
// Behavior follows the design prototype: the lead is saved when the contact
// step is submitted, photos upload as soon as they are picked, the review
// step can send the seller back to edit a section, and an unfinished form
// survives a reload on the same device for a week.

import type { AppConfig, FieldSpec, Preset, Step } from '../shared/config'
import type { Translate } from '../shared/i18n'
import { createPresenter, type Presenter } from '../shared/present'
import * as api from './api'
import { MAX_FILE_BYTES, compressPhoto, isPhotoFile } from './compress'
import {
  RETURN_KEY,
  REVIEW,
  SAVE_KEY,
  SOURCE_KEY,
  SUCCESS,
  WELCOME,
  activeSteps,
  clearStep,
  isEmpty,
  isStepBlank,
  loadSaved,
  parseSource,
  payload,
  progress,
  rememberSource,
  screenIds,
  stepById,
  validateStep,
  type Answers,
  type Errors,
  type Saved,
  type Value,
} from './engine'

export interface PhotoItem {
  slot: string | null
  status: 'uploading' | 'done' | 'error'
  progress: number
  url: string
  serverId?: number
  error?: string
  errorParams?: Record<string, string | number>
}

const AUTO_ADVANCE_MS = 300

function storage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null // private mode or blocked storage: the form still works
  }
}

function session(): Storage | null {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

export class FormState {
  readonly config: AppConfig
  readonly preset: Preset
  readonly t: Translate
  readonly ids: string[]
  readonly present: Presenter

  screen = $state(WELCOME)
  dir = $state(1)
  answers = $state<Answers>({})
  otherMake = $state(false)
  consent = $state(false)
  errors = $state<Errors>({})
  busy = $state(false)
  leadId = $state<number | null>(null)
  token = $state<string | null>(null)
  saveFailed = $state(false)
  submitFailed = $state(false)
  // The server refused because this network sent too many inquiries.
  limited = $state(false)
  // Honeypot on the contact step: people never see it, bots fill it in.
  trap = $state('')
  fromReview = $state(false)
  photos = $state<Record<string, PhotoItem>>({})
  saved = $state<Saved | null>(null)
  showOlderYears = $state(false)
  width = $state(390)
  // Bumped to shake the primary button when a step cannot be left.
  nudges = $state(0)

  wide = $derived(this.width >= 880)

  get step(): Step | undefined {
    return stepById(this.preset, this.screen)
  }

  /** An optional step with nothing answered: Continue waits for an answer, Skip moves on. */
  get waitsForAnswer(): boolean {
    const step = this.step
    if (!step?.skippable || step.fields.some((f) => f.type === 'photos' || f.required)) return false
    return isStepBlank(step, this.answers)
  }

  get progress() {
    return progress(this.ids, this.screen)
  }

  private advanceTimer: ReturnType<typeof setTimeout> | undefined
  private extraCounter = 0

  constructor(config: AppConfig) {
    this.config = config
    this.preset = config.preset
    this.present = createPresenter(config)
    this.t = this.present.t
    this.ids = screenIds(config.preset)
    this.saved = loadSaved(storage()?.getItem(SAVE_KEY) ?? null, Date.now())
    this.trackSource()
    // Back from the privacy policy: the step the seller left, not the welcome.
    if (this.saved && session()?.getItem(RETURN_KEY)) void this.resume()
    session()?.removeItem(RETURN_KEY)
  }

  // The consent step's policy link opens in this tab; the answers are saved.
  leaveForPolicy = () => {
    session()?.setItem(RETURN_KEY, '1')
  }

  // --- formatting (shared with the dashboard) ---------------------------------

  formatNumber(value: number): string {
    return this.present.formatNumber(value)
  }

  get currencySymbol(): string {
    return this.present.currencySymbol
  }

  get currencyAfter(): boolean {
    return this.present.currencyAfter
  }

  formatMoney(value: number): string {
    return this.present.formatMoney(value)
  }

  unit(kind: 'short' | 'long'): string {
    return this.present.unit(kind)
  }

  fieldLabel(field: FieldSpec, place: 'form' | 'review' = 'form'): string {
    return this.present.fieldLabel(field, place)
  }

  // A field's answer as a person reads it.
  display(field: FieldSpec, value: Value | undefined): string {
    return this.present.display(field, value)
  }

  errorText(fieldId: string): string {
    const error = this.errors[fieldId]
    if (!error) return ''
    const field = this.findField(fieldId)
    const params: Record<string, string | number> = {
      unit: this.unit('short'),
      unit_long: this.unit('long'),
      ...error.params,
    }
    // Limits are shown the way the field is shown: $100, 950,000.
    for (const key of ['min', 'max', 'value'] as const) {
      const raw = error.params?.[key]
      if (typeof raw === 'number' && field?.widget !== 'year_grid') {
        params[key] = field?.unit === 'currency' ? this.formatMoney(raw) : this.formatNumber(raw)
      }
    }
    const specific = `preset.fields.${fieldId}.errors.${error.code}`
    const text = this.t(specific, params)
    return text === specific ? this.t(`errors.${error.code}`, params) : text
  }

  findField(id: string): FieldSpec | undefined {
    return this.present.findField(id)
  }

  // --- answers ---------------------------------------------------------------

  set(fieldId: string, value: Value | undefined) {
    this.answers = { ...this.answers, [fieldId]: value }
    if (this.errors[fieldId] || (fieldId === 'contact_method' && this.errors.email)) {
      const errors = { ...this.errors }
      delete errors[fieldId]
      if (fieldId === 'contact_method') delete errors.email
      this.errors = errors
    }
  }

  autoAdvance() {
    clearTimeout(this.advanceTimer)
    this.advanceTimer = setTimeout(() => this.next(), AUTO_ADVANCE_MS)
  }

  // --- navigation ------------------------------------------------------------

  private go(screen: string, dir: number) {
    clearTimeout(this.advanceTimer)
    this.errors = {}
    this.dir = dir
    this.screen = screen
    this.persist()
  }

  private following(screen: string): string {
    return this.ids[this.ids.indexOf(screen) + 1]
  }

  next = async () => {
    clearTimeout(this.advanceTimer)
    if (this.busy) return
    const screen = this.screen
    if (screen === WELCOME) return this.go(this.ids[1], 1)
    if (screen === REVIEW) return this.submit()

    const step = this.step
    if (!step || this.waitsForAnswer) return
    if (step.fields.some((field) => field.type === 'photos')) {
      if (Object.values(this.photos).some((photo) => photo.status === 'uploading')) {
        this.errors = { photos: { code: 'wait' } }
        this.nudges++
        return
      }
      return this.go(this.fromReview ? this.leave() : REVIEW, 1)
    }

    const errors = validateStep(step, this.answers)
    if (this.otherMake && step.fields.some((f) => f.id === 'make') && isEmpty(this.answers.make)) {
      errors.make = { code: 'other_required' }
    }
    if (step.consent && !this.consent) errors.consent = { code: 'consent' }
    if (Object.keys(errors).length) {
      this.errors = errors
      this.nudges++
      return
    }
    if (step.submit) return this.saveLead()
    this.go(this.fromReview ? this.leave() : this.following(screen), 1)
  }

  private leave(): string {
    this.fromReview = false
    return REVIEW
  }

  back = () => {
    clearTimeout(this.advanceTimer)
    if (this.busy) return
    if (this.fromReview) return this.go(this.leave(), -1)
    const index = this.ids.indexOf(this.screen)
    if (index > 0) this.go(this.ids[index - 1], -1)
  }

  skip = () => {
    const step = this.step
    if (!step) return
    if (step.fields.some((field) => field.type === 'photos')) return this.go(REVIEW, 1)
    this.answers = clearStep(step, this.answers)
    this.go(this.fromReview ? this.leave() : this.following(this.screen), 1)
  }

  edit = (screen: string) => {
    this.fromReview = true
    this.go(screen, -1)
  }

  // --- saving ----------------------------------------------------------------

  private async saveLead() {
    this.busy = true
    this.saveFailed = false
    try {
      const answers = payload(this.preset, this.answers)
      if (this.leadId && this.token) {
        await api.updateLead(this.leadId, this.token, answers)
      } else {
        const created = await api.createLead(answers, storage()?.getItem(SOURCE_KEY) ?? null, this.trap)
        this.leadId = created.id
        this.token = created.token
      }
      this.busy = false
      const target = this.fromReview ? this.leave() : this.following(this.screen)
      this.go(target, 1)
    } catch (error) {
      this.busy = false
      this.handleSaveError(error)
    }
  }

  private handleSaveError(error: unknown) {
    if (error instanceof api.ApiError && error.status === 422 && Object.keys(error.errors).length) {
      // The server disagreed with an answer: show it where it was given.
      const [first] = Object.keys(error.errors)
      const owner = activeSteps(this.preset).find((step) =>
        step.fields.some((f) => f.id === first || f.follow_up?.fields.some((c) => c.id === first)),
      )
      if (owner && owner.id !== this.screen) this.go(owner.id, -1)
      this.errors = error.errors
    } else {
      this.saveFailed = true
      this.limited = error instanceof api.ApiError && error.status === 429
    }
    this.nudges++
  }

  private async submit() {
    if (!this.leadId || !this.token) return
    this.busy = true
    this.submitFailed = false
    try {
      // Sections edited from the review step are saved together with the submit.
      await api.updateLead(this.leadId, this.token, payload(this.preset, this.answers))
      await api.submitLead(this.leadId, this.token)
      this.busy = false
      this.go(SUCCESS, 1)
      storage()?.removeItem(SAVE_KEY)
    } catch (error) {
      this.busy = false
      if (error instanceof api.ApiError && error.status === 422) return this.handleSaveError(error)
      this.submitFailed = true
      this.limited = error instanceof api.ApiError && error.status === 429
      this.nudges++
    }
  }

  // --- saved progress --------------------------------------------------------

  persist() {
    const store = storage()
    if (!store) return
    if (this.screen === SUCCESS || (this.screen === WELCOME && !this.leadId)) return
    const saved: Saved = {
      step: this.screen,
      answers: this.answers,
      otherMake: this.otherMake,
      leadId: this.leadId ?? undefined,
      token: this.token ?? undefined,
      savedAt: Date.now(),
    }
    try {
      store.setItem(SAVE_KEY, JSON.stringify(saved))
    } catch {
      // quota or privacy mode: saving progress is a convenience only
    }
  }

  resume = async () => {
    const saved = this.saved
    if (!saved) return
    this.answers = saved.answers
    this.otherMake = saved.otherMake
    this.leadId = saved.leadId ?? null
    this.token = saved.token ?? null
    this.consent = Boolean(saved.leadId)
    this.saved = null
    this.go(this.ids.includes(saved.step) ? saved.step : this.ids[1], 1)
    if (this.leadId && this.token) await this.restorePhotos()
  }

  private async restorePhotos() {
    try {
      const lead = await api.fetchLead(this.leadId!, this.token!)
      const photos: Record<string, PhotoItem> = {}
      for (const photo of lead.photos) {
        const key = photo.slot ?? `x${this.extraCounter++}`
        photos[key] = {
          slot: photo.slot,
          status: 'done',
          progress: 1,
          url: api.thumbSrc(photo, this.token!),
          serverId: photo.id,
        }
      }
      this.photos = photos
    } catch {
      // The lead is gone or the token expired: start the photos afresh.
      this.leadId = null
      this.token = null
    }
  }

  restart = () => {
    clearTimeout(this.advanceTimer)
    storage()?.removeItem(SAVE_KEY)
    this.answers = {}
    this.otherMake = false
    this.consent = false
    this.leadId = null
    this.token = null
    this.photos = {}
    this.saved = null
    this.fromReview = false
    this.saveFailed = false
    this.submitFailed = false
    this.showOlderYears = false
    this.go(WELCOME, -1)
  }

  private trackSource() {
    const params = new URLSearchParams(window.location.search)
    const incoming = parseSource(params.get('src'))
    const store = storage()
    if (incoming && store) {
      const kept = rememberSource(store.getItem(SOURCE_KEY), incoming)
      if (kept) store.setItem(SOURCE_KEY, kept)
    }
    if (params.has('src')) {
      params.delete('src')
      const query = params.toString()
      history.replaceState(null, '', `${location.pathname}${query ? `?${query}` : ''}${location.hash}`)
    }
  }

  // --- photos ----------------------------------------------------------------

  get photosField(): FieldSpec | undefined {
    return this.preset.steps.flatMap((s) => s.fields).find((f) => f.type === 'photos')
  }

  addPhotos = async (slot: string | null, files: File[]) => {
    const field = this.photosField
    if (!field || !files.length) return
    if (slot) return this.addPhoto(slot, slot, files[0])
    const room = field.extra - Object.values(this.photos).filter((p) => p.slot === null).length
    if (room <= 0) {
      this.errors = { photos: { code: 'limit', params: { max: field.extra } } }
      return
    }
    for (const file of files.slice(0, room)) {
      await this.addPhoto(`x${this.extraCounter++}`, null, file)
    }
  }

  private async addPhoto(key: string, slot: string | null, file: File) {
    const errors = { ...this.errors }
    delete errors.photos
    this.errors = errors
    const previous = this.photos[key]
    const fail = (error: string, errorParams?: Record<string, string | number>) => {
      this.photos = { ...this.photos, [key]: { slot, status: 'error', progress: 0, url: '', error, errorParams } }
    }
    if (!isPhotoFile(file)) return fail('not_photo')
    if (file.size > MAX_FILE_BYTES) return fail('too_big', { size: Math.round(file.size / 1048576) })

    const url = URL.createObjectURL(file)
    this.photos = { ...this.photos, [key]: { slot, status: 'uploading', progress: 0, url } }
    try {
      const blob = await compressPhoto(file)
      const uploaded = await api.uploadPhoto(this.leadId!, this.token!, blob, slot, (fraction) => {
        const current = this.photos[key]
        if (current?.status === 'uploading') {
          this.photos = { ...this.photos, [key]: { ...current, progress: Math.min(fraction, 0.99) } }
        }
      })
      if (!this.photos[key]) return // removed while uploading
      this.photos = { ...this.photos, [key]: { slot, status: 'done', progress: 1, url, serverId: uploaded.id } }
      if (previous?.url.startsWith('blob:')) URL.revokeObjectURL(previous.url)
    } catch (error) {
      const code = error instanceof api.ApiError ? error.errors.photos?.code : undefined
      fail(code === 'format' ? 'not_photo' : 'failed')
      URL.revokeObjectURL(url)
    }
  }

  removePhoto = async (key: string) => {
    const photo = this.photos[key]
    if (!photo) return
    const photos = { ...this.photos }
    delete photos[key]
    this.photos = photos
    if (photo.serverId && this.leadId && this.token) {
      try {
        await api.deletePhoto(this.leadId, this.token, photo.serverId)
      } catch {
        // Already gone on the server, or offline: the owner simply sees one photo more.
      }
    }
  }

  get donePhotos(): PhotoItem[] {
    const order = this.photosField?.slots.map((slot) => slot.id) ?? []
    return Object.values(this.photos)
      .filter((photo) => photo.status === 'done')
      .sort((a, b) => {
        const ai = a.slot ? order.indexOf(a.slot) : order.length
        const bi = b.slot ? order.indexOf(b.slot) : order.length
        return ai - bi
      })
  }
}
