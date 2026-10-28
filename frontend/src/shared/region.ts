// What depends on the client's country: how phone numbers and postal codes
// are checked and shown, with the same rules as app/services/validation.py.
// The country comes from the form preset (phone_region, and postal_code_format
// or postal_code_pattern). US numbers use the small rules below; any other
// country uses libphonenumber, which is loaded only for a client outside the
// US (it adds about 30 KB).
import type { CountryCode, PhoneNumber } from 'libphonenumber-js/min'
import type { Preset } from './config'

type Library = typeof import('./phoneLibrary')

const US_ZIP_RE = /^\d{5}(-\d{4})?$/

let home = 'US'
let library: Library | null = null
let postalCode = US_ZIP_RE

export async function prepareRegion(
  preset: Pick<Preset, 'phone_region'> & Partial<Pick<Preset, 'postal_code_pattern'>>,
): Promise<void> {
  home = preset.phone_region
  postalCode = preset.postal_code_pattern ? new RegExp(`^(?:${preset.postal_code_pattern})$`) : US_ZIP_RE
  if (home !== 'US' && !library) library = await import('./phoneLibrary')
}

/** E.164 form of a number typed at home (+14155550142), or null if it can't be one. */
export function normalizePhone(raw: string): string | null {
  if (home === 'US' || !library) return normalizeUsPhone(raw)
  const number = parse(raw)
  const sameCode = number?.countryCallingCode === library.getCountryCallingCode(home as CountryCode)
  return number?.isValid() && sameCode ? number.number : null
}

export function normalizeUsPhone(raw: string): string | null {
  let digits = raw.replace(/\D/g, '')
  if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1)
  if (digits.length !== 10 || '01'.includes(digits[0]) || '01'.includes(digits[3])) return null
  return `+1${digits}`
}

export function isPostalCode(raw: string): boolean {
  return postalCode.test(raw.trim())
}

/**
 * How a stored number reads: (415) 555-0142 in the US, 8 (912) 345-67-89 for
 * a Russian number in Russia, and in international form when it comes from
 * another country. Anything that is not a number is shown as it is.
 */
export function formatPhone(value: string): string {
  if (home === 'US' || !library) return formatUsPhone(value)
  const number = parse(value)
  if (!number) return value
  return number.country === home ? number.formatNational() : number.formatInternational()
}

function formatUsPhone(value: string): string {
  const trimmed = value.trim()
  if (trimmed.startsWith('+') && !trimmed.startsWith('+1')) return value
  let digits = trimmed.replace(/\D/g, '')
  if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1)
  if (digits.length !== 10) return value
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`
}

function parse(raw: string): PhoneNumber | undefined {
  return library?.parsePhoneNumberFromString(raw, home as CountryCode)
}
