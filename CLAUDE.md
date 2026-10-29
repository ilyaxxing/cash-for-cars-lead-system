# Cash for Cars Lead System

> **Setting up an instance for a business?** If the person you are helping wants
> to install or launch this system, for a client or for their own business,
> follow [SETUP.md](SETUP.md) step by step (also `/setup-client`). The rest of
> this file is for changing the code.

Lead intake for "we buy cars" dealers, installed one business at a time.
Business-card-size cards with a QR code, left under the windshield wipers of
parked cars (the main channel) → mobile web form for the car seller → Postgres →
Web Push to the owner → owner dashboard (PWA, must work on iPhone).
One instance per client (separate Railway project), not multi-tenant.

The repository is public. Write everything as if strangers read it.

## Hard rules
- Code, comments, README, commits: English. UI text only in `locales/en.json`,
  a client's own `LOCALE_FILE`, or a country's starting files in
  `countries/<code>/` (its texts, and the demo's in `demo.yaml`); code uses
  keys. Target market and reader: US; other countries through client files
  started from `countries/` (docs/customize-the-form.md, Another country),
  never by forking the code. Their translations had no native speaker's
  review yet; say so wherever they are offered.
- Never commit `.env`, secrets (tokens, passwords, VAPID keys, bucket keys),
  DB dumps/backups, uploaded photos, real client data (names, phones,
  domains, tax IDs). Client-specific values come only from env and the preset.
- Pre-commit hook: `git config core.hooksPath .githooks` → `tools/check_secrets.sh`
  (gitleaks + `tools/pii_scan.py`). Before every push: `tools/check_secrets.sh --all`
  and the test suite. Failing tests or a finding → fix first, never push.
- Conventional Commits, one logical change per commit. Commit email is the
  GitHub noreply address (repo-local git config).
- `main` always works. Every change on its own branch, merged via PR after
  the tests pass (CI runs them) and, for UI, a browser check. Installers
  deploy release tags, not `main`. No force push unless the user asks.
- Some logic and many lessons come from an earlier Telegram bot by the same
  author (not public); they are written down where they apply.
- Default brand "Car Buyout"; `BRAND_NAME` overrides.
  The privacy-consent operator is the client (`OPERATOR_NAME`).
- Installers are usually not technical and follow SETUP.md through Claude
  Code. Keep SETUP.md, the deploy script's messages, the README and docs/ in step
  with any change they touch.

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy async + asyncpg, Alembic,
  pydantic-settings. Package `app/`.
- Frontend: Svelte 5 + Vite + TypeScript, two separate bundles (seller form at `/`,
  dashboard PWA at `/app/`), served by FastAPI. Node only at image build time.
  Chosen because the designs are HTML templates with if/for and inline styles,
  which map onto Svelte almost 1:1. Fonts (Geist, Geist Mono) self-hosted.
- Project page (`docs/index.html`, GitHub Pages) with a live demo (`docs/demo`):
  the real bundles plus a stand-in server that runs in the browser
  (`frontend/src/demo`, typed against the API modules, never part of an
  instance), built by `tools/make_demo.py`. Rebuild it after UI changes.
  One demo per country in `countries/` (the US at `docs/demo`, the others at
  `docs/demo/<code>/`), each with that country's settings and the fictional
  business, leads, prices and units of its `demo.yaml`; calls and messages
  show a notice instead of dialing. Demo phone numbers must be ones
  `tools/pii_scan.py` knows to be fictional (tests/test_countries.py).
  The page installers send a car buyer (`buyer-site/index.html`, a template
  filled per country by `tools/make_buyer_site.py`: the US at the root, the
  others at `/<code>/`) is a site of its own, https://car-buyer-demo.github.io/ (the
  `car-buyer-demo` organization's Pages), so its address cannot be shortened
  to the project page: the same demo in that business's name, color and
  language from the link, no prices, setup or links back to this repository.
- Hosting, one instance per client, two ways. The domain is the client's
  own, in their name, and required: QR codes and cards are made only for it
  (the commands refuse a `*.up.railway.app` address).
  - Railway (`tools/deploy.py`), the default. Per client: app service `app`
    (1 replica: in-memory rate limits and background jobs) + `Postgres`
    (point-in-time recovery, turned on by the deploy script; Railway keeps
    about 4 weeks) + bucket `photos` (S3-compatible, no Railway backups).
    Built on the installer's Railway account, then transferred to the
    client's own (Transfer Ownership: the client pays; the installer stays an
    Editor for support).
  - A server of the client's own (`tools/deploy_vps.py`, `deploy/vps/`): any
    Linux server over SSH, for a country whose law keeps data at home or a
    business that cannot pay Railway. Docker compose with the app, PostgreSQL
    with a daily dump on the same server (`BACKUP_DAYS`, 14), and Caddy for
    HTTPS (Let's Encrypt); photos on a volume.
- Deploy scripts: the client's env file in, a working URL out. Both wait for
  `/healthz` to report the uploaded git sha and the Alembic head (lesson from
  the bot: never assume a deploy came up). `docker-compose.dev.yml` is
  for local development only. `tools/deploy.py` drives the Railway CLI step
  by step, not `.railway/railway.ts` IaC: IaC deletes every variable it does
  not list (the bot nearly lost its secrets that way) and railway.toml stops
  working on 2026-12-01. Client files live in git-ignored `clients/`;
  SECRET_KEY and VAPID keys are generated once and written back there.
  Database and bucket credentials are Railway references (`${{Postgres...}}`,
  `${{photos...}}`); secrets go over stdin. GIT_SHA is a service variable that
  the Dockerfile reads as a build arg (`railway up` sets no commit sha).

## Designs (source of truth for UI, repeat exactly)
Claude Design projects "Seller Flow" and "Buyer Dashboard" (US market variant:
miles, USD, ZIP, US phone format). Agreed deviations:
- Seller steps: Welcome → Vehicle → Year & mileage → Condition → Accident (+details)
  → Finance/lien (+details) → Price (skippable) → Location city+ZIP (skippable)
  → VIN (separate step, skippable) → Contact & consent → Photos → Review → Success.
- After Contact the lead is saved and the owner is notified ("no photos").
  Photos upload right after picking; skip label "I'll send later". Final
  submit on Review marks the lead submitted (one more push if it has photos).
  Unfinished form resumes on the same device (localStorage, max 7 days);
  the consent step's policy link opens in the same tab, and back from it
  the form goes straight to that step (sessionStorage flag).
- Accident and lien: Yes / No / Don't know (third tile added in design style).
- Photo tiles open the system picker directly (iOS offers camera or library
  there); the design's action sheet is unused in the prototype, so it is not built.
- Illustrations: sources go to `design-reference/` (git-ignored), the app ships
  WebP versions in `frontend/src/assets/illustrations/` (hero in several widths
  for srcset, guides named as in the preset). Guide sources are pencil sketches
  on light paper (`design-reference/guide-<slot>.jpg`); `tools/make_guides.py`
  redraws them in two colors, paper = the empty tile's `--surface-sunken`,
  pencil = a soft light line, dense interior sketches dimmed to match.
- Brand mark: the design's lime rounded square, with a dark price tag instead
  of the design's dot (chosen by the owner; `shared/TagGlyph.svelte`, and
  `app/branding/mark.py` for the home-screen icons). The $ shows only where
  the mark is large: sign-in screen and app icons.
- Client branding (`app/branding/`): the defaults are the owner's own look
  (lime, price-tag mark, car photo). `BRAND_COLOR` recolors every accent
  (the server injects CSS variables; no hard-coded accent colors in the
  frontend), `BRAND_LOGO`/`BRAND_ICON`/`BRAND_PHOTO` replace the mark, the
  home-screen icon and the welcome photo. Icons are drawn by the app, not
  shipped as files. The installer is asked item by item what to change;
  anything not changed stays default.
- Business card (`python -m app.cli card`): our own design, deliberately not
  a copy of the card the owner made for a client. Print-ready by rule: vector
  CMYK PDF in the client's country size (`CARD_SIZE`: 3.5x2in, 90x50mm,
  85x55mm, any metric card from 85x50 to 92x56mm) with that country's bleed
  and page boxes, fonts embedded (`CARD_FONT` for scripts Geist lacks; never a
  missing letter, no joining scripts yet), text >= 7 pt and
  >= 0.2 in inside the trim, flat rich-black background under 300% ink, QR and
  small gray text in black ink only, black overprints on the accent.
- No manufacturer badges or emblems in shipped images (trademarks). They are
  retouched out of the sources: `design-reference/hero-car-clean.png` and the
  `guide-<slot>.jpg` sketches. A new illustration gets the same treatment
  before it is converted.
- Contact: name, phone (required), email (optional, personal data), preferred
  contact method (call, SMS, WhatsApp, email). Telegram is opt-in per client
  (one line in the preset; texts ship), and the lead's messenger button opens
  Telegram instead of WhatsApp for a seller who chose it.
- Status: design's 4-way switch; confirmation dialog for Purchased and Rejected,
  undo toast for others. Any transition allowed; `closed_at` set on entering a
  closed status, cleared on leaving it.
- Notes: list with timestamps and delete (design). Activity log per lead.
- List cards exactly as in design (general info); full details inside the lead.
- Dates and times use the US convention through Intl ("Oct 2, 2:05 PM") instead
  of the prototype's 24-hour "2 Oct, 14:05"; phone numbers read "(415) 555-0142".
- Leads open at /app/leads/<id> (used by push notifications), statistics at
  /app/stats, settings at /app/settings.
- No email at all: notifications are Web Push only. Dashboard shows a warning
  when there is no working push subscription or the last push failed.
  Settings has no "Backup email" section.
- Not in the design, built in the same visual system and shown for approval:
  login, onboarding (Add to Home Screen for iOS/Android, enable push, test push),
  Help in Settings, privacy policy page, WhatsApp button in the lead.

## Data model
`leads` fixed columns: make, model, year, mileage, asking_price, location, phone,
name, status, source, has_photos, created_at, closed_at. Everything else from
the form goes to `answers` JSONB, so a new preset field needs no migration.
Technical columns: preset_id, viewed_at, submitted_at, status_changed_at,
purged_at, updated_at. Notes, activity events and photos are separate tables.
Statuses (from the bot, stored as text, not enum): new, in_work, bought, rejected.
Labels from the design: New, In Progress, Purchased, Rejected.

## Logic carried over from the bot
- Source label: first meaningful source wins; a new label only overwrites the
  default `direct`. Frozen on the lead at creation. Format `[A-Za-z0-9_-]{1,64}`,
  lowercased. `/v` → `card` ("Business Card"), `?src=` for others, labels via
  `SOURCE_LABELS`; unknown labels show as "Other" and log a warning.
- Retention: 90 days after closing (not creation), name, phone, every preset
  field marked `personal: true` and the photos (objects, then rows) are wiped;
  rows stay for statistics. Photos were added to the bot's scope: plates, faces
  and driveways identify the seller. VIN stays (car data); a number plate
  (`registration`, asked instead of the VIN in some countries) is personal:
  a registry ties it to the owner. Owner notes stay
  (the help says not to put contacts there). `purged_at`
  distinguishes "never given" from "deleted by retention". Daily background pass,
  first pass at startup, one log line per pass even when nothing was purged,
  errors never crash the app. The period lives in one place.
- Nothing is stored before the Contact step: abandoned forms leave no rows.
- Never log personal data; logs carry ids only.
- Privacy policy must be honest about what retention cannot reach (backups until
  their rotation, notifications already shown). Not legal advice: the client's
  lawyer reviews it.

## Preset
`presets/us-car-buyout.yaml` describes steps and fields: id, type (text, number,
select, yes_no, photos, phone), required, options, unit, follow_up, plus UI hints
(widget, levels, photo slots). No UI text in the preset; keys are derived from ids.
Field id equal to a fixed column → stored in the column, otherwise in `answers`.
Invalid preset → the app refuses to start.

## Abuse, addresses and QR codes
- Spam: a honeypot input named `referral_code` (AutoFill never fills it); a
  filled honeypot gets a convincing answer and nothing is stored. Seller
  limits per address: 10 new leads and 600 requests per hour (carrier NAT),
  counted in memory; the IP address is never stored or logged.
- The address comes from CLIENT_IP_HEADER (X-Real-IP: set by the Railway deploy
  script; Caddy sets it on a server of the client's own), never from
  X-Forwarded-For: uvicorn with --forwarded-allow-ips='*' takes its first
  entry, so behind a proxy that passes a client's own value through, the
  limits and the login limit could be reset at will. Railway's edge replaces
  X-Real-IP with the real address (checked live on 2026-10-20).
- QR codes: `python -m app.cli qr`, error correction H, a 4-module quiet zone,
  at least 0.4 mm per module at 20 mm.
