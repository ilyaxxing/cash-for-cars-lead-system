// The two libphonenumber functions region.ts uses, in their own module so the
// lazily loaded chunk carries only what they need.
export { getCountryCallingCode, parsePhoneNumberFromString } from 'libphonenumber-js/min'
