// Instance configuration: brand, preset and interface texts.
// In production it is baked into the page by the server (see app/web/pages.py);
// under the Vite dev server it is fetched from the API instead.

export type Messages = { [key: string]: string | Messages }

export interface PresetOption {
  id: string
  level?: number
}

export interface PhotoSlot {
  id: string
  image: string
  ratio: string
}

export interface FieldSpec {
  id: string
  type: 'text' | 'number' | 'select' | 'yes_no' | 'photos' | 'phone'
  required: boolean
  required_when?: Record<string, string>
  personal: boolean
  options: PresetOption[]
  default?: string
  unknown: boolean
  flag?: string
  follow_up?: { when: string; fields: FieldSpec[] }
  max_length?: number
  multiline: boolean
  format?: 'vin' | 'email' | 'postal_code'
  min?: number
  max?: number
  unit?: 'distance' | 'currency'
  recent?: number
  earlier?: number
  widget?: 'tiles' | 'chips' | 'year_grid'
  suggestions: string[] | Record<string, string[]>
  suggestions_by?: string
  other: boolean
  chip: boolean
  slots: PhotoSlot[]
  extra: number
}

export interface Step {
  id: string
  fields: FieldSpec[]
  enabled: boolean
  skippable: boolean
  submit: boolean
  consent: boolean
  note?: 'box' | 'icon' | 'text'
  show_chips: boolean
  group?: string
}

export interface Preset {
  id: string
  version: number
  distance_unit: 'mi' | 'km'
  phone_region: string
  postal_code_format?: string
  postal_code_pattern?: string
  steps: Step[]
}

// The client's logo and welcome photo (BRAND_LOGO, BRAND_PHOTO), prepared by
// the server; null means the designs' own mark and photo.
export interface Logo {
  url: string
  width: number
  height: number
  // Wide enough to be a wordmark: it spells the name, so it stands alone.
  wordmark: boolean
}

export interface Photo {
  src: string
  srcset: string
  width: number
  height: number
}

export interface Brand {
  name: string
  phone: string
  logo: Logo | null
  photo: Photo | null
}

export interface AppConfig {
  brand: Brand
  operator: string
  locale: string
  currency: string
  timezone: string
  preset: Preset
  messages: Messages
  privacyUrl: string
  retentionDays: number
}

export async function loadConfig(): Promise<AppConfig> {
  const block = document.getElementById('app-config')
  if (block?.textContent) {
    return JSON.parse(block.textContent) as AppConfig
  }
  const response = await fetch('/api/config')
  if (!response.ok) {
    throw new Error(`config request failed: ${response.status}`)
  }
  return (await response.json()) as AppConfig
}
