# Configuration

Every setting, and how a client's look (color, logo, icon, photo) is configured.

All settings are environment variables; [.env.example](../.env.example) lists
them with comments. On Railway they are service variables of the `app`
service, set by the deploy script from the client's file.

| Setting | Default | Notes |
|---|---|---|
| `APP_ENV` | `development` | `production` refuses to start with a missing secret or setting. |
| `PUBLIC_URL` | Railway address | Used in notification links and the privacy policy. |
| `SECRET_KEY` | | 32+ characters. Signs owner sessions and sellers' upload tokens. |
| `CLIENT_IP_HEADER` | | Header the hosting proxy fills with the visitor's address, for rate limits. `X-Real-IP` on Railway (set by the deploy script; Railway replaces any value a client sends). Never `X-Forwarded-For`: many proxies pass a client's own value through. |
| `PRESET`, `LOCALE` | `us-car-buyout`, `en` | Files in `presets/` and `locales/`. |
| `PRESET_FILE`, `LOCALE_FILE`, `PRIVACY_POLICY_FILE` | | A client's own form, texts and privacy policy, for a market the shipped files don't cover; see [Customize the form](customize-the-form.md#another-country). |
| `CURRENCY`, `TIMEZONE` | `USD`, `America/New_York` | |
| `BRAND_NAME`, `BRAND_PHONE` | `Car Buyout` | The phone may be written any way; the privacy policy and the business card show it as people in the form's country write it, e.g. (512) 555-0100. |
| `BRAND_COLOR` | `#C7F747` | Accent color. Refused if too dark for the dark screens; the error suggests a lighter shade. |
| `BRAND_LOGO`, `BRAND_ICON`, `BRAND_PHOTO` | | Image files (PNG, JPEG, WebP), relative to the repository. Checked at startup; see [Client branding](#client-branding). |
| `CARD_SIZE` | `3.5x2in` | The business card's size: `3.5x2in` (US), `90x50mm` (Russia), `85x55mm` (Europe), each with the bleed shops there ask for, or any card from `85x50mm` to `92x56mm` (3 mm bleed), e.g. `91x55mm` in Japan. |
| `CARD_FONT` | | A font for card text in scripts the card's own font (Geist: Latin, Cyrillic) lacks, such as Chinese, Korean, Japanese or Greek: a static TrueType `.ttf` file, e.g. Noto Sans SC Bold from Google Fonts. Used by the card command only; never sent to the server. |
| `OPERATOR_NAME`, `OPERATOR_EMAIL`, `OPERATOR_ADDRESS`, `POLICY_EFFECTIVE_DATE` | | Privacy policy and consent. Name and email are required in production. |
| `OWNER_PASSWORD` | | The owner's first dashboard password: it opens the dashboard until the owner sets a password of their own, which the first sign-in asks for before anything else. Changing it here and restarting resets the owner's password to it, signs every device out and asks again: the way back in when it is forgotten. |
| `DATABASE_URL` | local | Any PostgreSQL URL; converted to the async driver. |
| `STORAGE_BACKEND` | `local` | `local` for development. In production `s3` (Railway), with `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`; or `volume`, a disk that outlives deploys (a server of the client's own, set by `tools/deploy_vps.py`). |
| `NOTIFY_CHANNELS` | `push` | |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` | | Web Push keys: `python -m app.cli vapid-keys`. |
| `SOURCE_LABELS` | | `id:Label` pairs for `?src=` placements. |
| `LOG_LEVEL` | `INFO` | Logs carry ids, never personal data. |

The app runs as a single replica: rate limits and background jobs
(notifications, retention) live in that one process.

## Client branding

Out of the box every instance has the same look: lime accent, a price-tag
mark next to `BRAND_NAME`, and a car on the welcome screen. Each part can be
replaced for a client, and anything left empty keeps the default.

- `BRAND_COLOR` recolors buttons, links, selected answers, the mark and the
  home-screen icon. The text on accent buttons switches between dark and
  white, whichever reads better. A color too dark for the dark screens is
  refused, with a lighter shade of it suggested.
- `BRAND_LOGO` replaces the mark in the headers and on the sign-in screen.
  Use light lettering on a transparent background (PNG); a mostly dark logo
  on transparency is refused because it would disappear. A logo at least
  1.8 times wider than tall counts as a wordmark and stands alone, without
  the name beside it.
- `BRAND_ICON` is the home-screen icon. Without it a roughly square logo is
  used, and otherwise the mark in `BRAND_COLOR`. The app draws all icon
  sizes from it.
- `BRAND_PHOTO` replaces the welcome photo: landscape, at least 1200 px wide.

The files are checked when the app starts; one that would look broken stops
the start with a message saying what to fix.

In a client's settings file the paths point at files on your machine, kept
next to it in `clients/<id>/` (ignored by git): for example
`BRAND_LOGO=clients/acme/logo.png`. The deploy script checks them the same
way before creating anything, uploads them into `brand/` next to the code,
and points the app at them there. To change the look later, replace a file
or a setting and deploy again. A phone keeps the icon the app was added
with until the app is removed from the home screen and added again.
