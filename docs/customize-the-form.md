# Customize the form

The questionnaire is data: a preset file for the questions and a locale file for the wording.

The questionnaire is described by a preset, [presets/us-car-buyout.yaml](../presets/us-car-buyout.yaml),
and its wording by [locales/en.json](../locales/en.json). The preset holds
structure only, no text.

A preset is a list of steps; each step has fields:

```yaml
steps:
  - id: price
    skippable: true        # shows "Skip"
    note: box              # a note under the fields: box, icon or text
    fields:
      - { id: asking_price, type: number, unit: currency, min: 100, max: 5000000 }
```

Field types: `text`, `number`, `select`, `yes_no`, `photos`, `phone`. Common
options:

| Option | Meaning |
|---|---|
| `required`, `required_when: {contact_method: email}` | Always, or only when another answer has a value. |
| `personal: true` | Personal data: hidden from list cards and erased by retention with the name and phone. |
| `options` (select), `unknown: true` (yes_no) | Choices; `unknown` adds "Don't know". |
| `flag: "yes"` | That answer puts a warning badge on the lead. |
| `follow_up: {when: "yes", fields: [...]}` | Extra fields shown for one answer. |
| `max_length`, `multiline`, `format` (`vin`, `email`, `postal_code`) | Text rules. |
| `min`, `max`, `unit` (`distance`, `currency`) | Number rules. |
| `widget` (`tiles`, `chips`, `year_grid`), `suggestions`, `chip` | How the form shows the field. |
| `slots`, `extra` | Photos: guided angles with their guide images, plus free photos. |

Fields whose id is a lead column (`make`, `model`, `year`, `mileage`,
`asking_price`, `location`, `name`, `phone`) are stored there. Every other
answer goes to the lead's `answers` JSON, so **a new field needs no database
migration**: add it to the preset, add its texts, deploy.

Texts are looked up by ids:

```json
"preset": {
  "steps":  { "price": { "tag": "Price", "title": "What price do you have in mind?", "hint": "…", "note": "…" } },
  "fields": { "asking_price": { "label": "Expected price", "errors": { "min": "…" } } },
  "options": { "condition": { "good": { "label": "Good" } } }
}
```

Step titles, field labels, option labels and photo labels are required. If
one is missing, or the preset is invalid, the app refuses to start and says
which key, and the deploy script stops before deploying. Run `tools/check.sh`
after editing: the tests load the shipped preset and texts too.

**Contact methods.** The seller picks one of the `contact_method` options;
the shipped preset offers `call`, `sms`, `whatsapp` and `email`. `telegram`
is built in as well (texts included) for businesses whose sellers use it:

```yaml
      - id: contact_method
        type: select
        default: call
        options:
          - { id: call }
          - { id: sms }
          - { id: whatsapp }
          - { id: telegram }
          - { id: email }
```

In the lead, the messenger button next to Call opens WhatsApp, or Telegram
for a seller who chose it (`t.me/+<number>`: Telegram finds the seller by
phone unless they have turned that off).

**Country.** The top of the preset says where the sellers are:

```yaml
distance_unit: mi           # or km
phone_region: US            # the sellers' country, as an ISO code: US, RU, DE
postal_code_format: us_zip  # a US ZIP code; elsewhere postal_code_pattern
```

Phone numbers are checked and shown the way people write them in that
country (the rules are libphonenumber's), and a number with another
country's calling code is refused. Outside the US, replace
`postal_code_format` with `postal_code_pattern`, a pattern the whole code
must match, e.g. `postal_code_pattern: '\d{6}'` in Russia. Keep it to digits,
letters, spaces and dashes: the browser and the server both check it.

## Another country

A business outside the US gets its own files, kept with its settings in
`clients/<id>/` and uploaded with them, not edited into `presets/` and
`locales/`: updates then reach every client without conflicts.

| Setting | File |
|---|---|
| `PRESET_FILE` | The form: a copy of the shipped preset with the country's questions, `distance_unit`, `phone_region` and postal code rule. Its `id` is stored on each lead. |
| `LOCALE`, `LOCALE_FILE` | The language code (`ru`, `de`, `zh-Hant` with its script where it has several, never the country) and the texts. For a language that ships (`en`), the file only needs the texts that change; otherwise it is a full translation of `locales/en.json`. |
| `PRIVACY_POLICY_FILE` | The privacy policy in that language and under that country's law, a template like `locales/privacy-policy.en.md`. A lawyer of the client's checks it. |
| `CURRENCY`, `TIMEZONE` | e.g. `RUB`, `Europe/Moscow`. Where a car costs millions in the currency, the price question's `max` goes up with it. |
| `CARD_SIZE`, `CARD_FONT` | The card's size there, and a font for card text in a script Geist lacks ([Configuration](configuration.md)). |

The app checks them at startup, and the deploy script checks them before it
uploads anything: a missing text or an invalid form stops it with the key or
the line to fix. For a full translation, `python -m app.cli check-texts
--env-file clients/<id>.env` also compares it with `locales/en.json`, key by
key, placeholders included. Dates, numbers and prices follow the language and the
country. Geist covers Latin, Latin Extended, Vietnamese and Cyrillic; in the
app, phones show other scripts in their own fonts, and on the business card
`CARD_FONT` sets them. Not supported yet: languages written right to left,
and on the card, scripts whose letters join (Arabic, Hindi, Thai).
[SETUP.md](../SETUP.md#another-country) has the full list of what to check
for a country.
