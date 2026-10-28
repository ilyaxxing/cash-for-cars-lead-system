// Calls to the seller API (app/web/seller_api.py).

import type { Errors, Value } from './engine'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly errors: Errors = {},
  ) {
    super(`request failed: ${status}`)
  }
}

interface ErrorBody {
  errors?: { field: string; code: string; params?: Record<string, string | number> }[]
}

async function request<T>(method: string, url: string, token: string | null, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const response = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const errors: Errors = {}
    if (response.status === 422) {
      const data = (await response.json().catch(() => ({}))) as ErrorBody
      for (const error of data.errors ?? []) errors[error.field] = { code: error.code, params: error.params }
    }
    throw new ApiError(response.status, errors)
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

export interface CreatedLead {
  id: number
  token: string
}

export interface ServerPhoto {
  id: number
  slot: string | null
  thumbUrl: string
}

export interface StoredLead {
  id: number
  answers: Record<string, Value>
  photos: ServerPhoto[]
  submitted: boolean
}

export const createLead = (answers: Record<string, Value>, source: string | null, honeypot: string) =>
  request<CreatedLead>('POST', '/api/leads', null, { answers, source, honeypot })

export const updateLead = (id: number, token: string, answers: Record<string, Value>) =>
  request<{ id: number }>('PATCH', `/api/leads/${id}`, token, { answers })

export const fetchLead = (id: number, token: string) =>
  request<StoredLead>('GET', `/api/leads/${id}`, token)

export const submitLead = (id: number, token: string) =>
  request<{ id: number }>('POST', `/api/leads/${id}/submit`, token)

export const deletePhoto = (id: number, token: string, photoId: number) =>
  request<void>('DELETE', `/api/leads/${id}/photos/${photoId}`, token)

export function thumbSrc(photo: ServerPhoto, token: string): string {
  return `${photo.thumbUrl}?token=${encodeURIComponent(token)}`
}

// XMLHttpRequest rather than fetch: fetch cannot report upload progress,
// and the progress bar is part of the design.
export function uploadPhoto(
  id: number,
  token: string,
  file: Blob,
  slot: string | null,
  onProgress: (fraction: number) => void,
): Promise<ServerPhoto> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api/leads/${id}/photos`)
    xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    xhr.onload = () => {
      if (xhr.status === 201) return resolve(JSON.parse(xhr.responseText) as ServerPhoto)
      let code = 'failed'
      try {
        code = (JSON.parse(xhr.responseText) as ErrorBody).errors?.[0]?.code ?? code
      } catch {
        // not JSON: keep the generic code
      }
      reject(new ApiError(xhr.status, { photos: { code } }))
    }
    xhr.onerror = () => reject(new ApiError(0))
    const form = new FormData()
    form.append('file', file, 'photo.jpg')
    if (slot) form.append('slot', slot)
    xhr.send(form)
  })
}
