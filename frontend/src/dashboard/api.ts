// Calls to the owner API (app/web/auth_api.py, app/web/owner_api.py).

import type { Value } from '../form/engine'

export class Unauthorized extends Error {}

export class RequestFailed extends Error {
  constructor(
    readonly status: number,
    readonly code?: string,
  ) {
    super(`request failed: ${status}${code ? ` (${code})` : ''}`)
  }
}

async function call<T>(method: string, url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (response.status === 401 && !url.endsWith('/login')) throw new Unauthorized()
  if (!response.ok) {
    const data = (await response.json().catch(() => ({}))) as { error?: string }
    throw new RequestFailed(response.status, data.error)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export type Status = 'new' | 'in_work' | 'bought' | 'rejected'
export type Tab = 'new' | 'in_work' | 'all'

export interface Photo {
  id: number
  slot: string | null
  thumbUrl: string
  url: string
}

export interface Card {
  id: number
  status: Status
  createdAt: string
  source: string
  sourceLabel: string
  answers: Record<string, Value>
  photoCount: number
  photos: Photo[]
}

export interface Note {
  id: number
  text: string
  createdAt: string
}

export interface LeadEvent {
  id: number
  kind: string
  from: Status | null
  to: Status | null
  createdAt: string
}

export interface Detail extends Card {
  submittedAt: string | null
  closedAt: string | null
  statusChangedAt: string
  purgedAt: string | null
  hasPhotos: boolean
  notes: Note[]
  events: LeadEvent[]
}

export interface LeadList {
  counts: Record<Tab, number>
  leads: Card[]
  hasMore: boolean
}

export interface Stats {
  period: '7' | '30' | 'all'
  total: number
  week: number
  weekStart: string
  purchased: number
  firstLeadAt: string | null
  sources: { source: string; label: string; leads: number; purchased: number }[]
  buckets: { start: string; leads: number; purchased: number }[]
}

export const me = () => call<{ authenticated: boolean; passwordChangedAt: string | null }>('GET', '/api/auth/me')
export const login = (password: string) => call<{ ok: boolean }>('POST', '/api/auth/login', { password })
export const logout = () => call<{ ok: boolean }>('POST', '/api/auth/logout')
export const changePassword = (current: string, next: string) =>
  call<{ ok: boolean }>('POST', '/api/auth/password', { current, new: next })

export const listLeads = (tab: Tab, query: string, offset = 0) =>
  call<LeadList>('GET', `/api/owner/leads?${new URLSearchParams({ tab, q: query, offset: String(offset) })}`)
export const getLead = (id: number) => call<Detail>('GET', `/api/owner/leads/${id}`)
export const setStatus = (id: number, status: Status, undo?: number) =>
  call<{ status: Status; event: LeadEvent | null }>('POST', `/api/owner/leads/${id}/status`, { status, undo })
export const addNote = (id: number, text: string) => call<Note>('POST', `/api/owner/leads/${id}/notes`, { text })
export const deleteNote = (id: number, noteId: number) => call<void>('DELETE', `/api/owner/leads/${id}/notes/${noteId}`)
export const restoreNote = (id: number, noteId: number) =>
  call<Note>('POST', `/api/owner/leads/${id}/notes/${noteId}/restore`)
export const getStats = (period: Stats['period']) => call<Stats>('GET', `/api/owner/stats?period=${period}`)

export interface PushStatus {
  configured: boolean
  publicKey: string
  devices: number
  workingDevices: number
  lastSuccessAt: string | null
  problem: boolean
}

export const pushStatus = () => call<PushStatus>('GET', '/api/owner/push')
export const savePushSubscription = (subscription: PushSubscriptionJSON) =>
  call<{ ok: boolean }>('POST', '/api/owner/push/subscriptions', subscription)
export const removePushSubscription = (endpoint: string) =>
  call<{ ok: boolean }>('POST', '/api/owner/push/unsubscribe', { endpoint })
export const sendTestPush = (endpoint?: string) =>
  call<{ delivered: number; failed: number }>('POST', '/api/owner/push/test', { endpoint })
