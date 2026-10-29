# Deploy and run an instance

How one client's instance is deployed to Railway and kept running. Installing for a client with Claude Code follows [SETUP.md](../SETUP.md), which drives the same steps.

Each client gets a separate Railway project: the app, a PostgreSQL database
with point-in-time recovery, and a storage bucket for photos. One command
creates or updates it.

## Before you start

- A [Railway](https://railway.com) account on the Hobby plan, and the
  [Railway CLI](https://docs.railway.com/cli), signed in with `railway login`
  (`railway login --browserless` where no browser opens: a link and a code).
  The instance is built here and then handed over to the client's own
  Railway account (see [Hand over](#hand-over)).
- The client's own Railway account on the Hobby plan, with the client's
  payment card, and the client's domain.
- This repository with the Python environment from
  [local setup](development.md#local-setup) (the deploy script validates the
  settings with the app's own code). Node.js is not needed: the frontend is
  built on Railway.
- A clean git checkout of the commit you want to ship.

## 1. Create the client's settings file

```bash
mkdir -p clients
cp .env.example clients/acme.env
```

`clients/` is ignored by git: the file holds the client's secrets. Keep a copy
somewhere safe, such as a password manager. Fill in at least:

| Setting | What to put there |
|---|---|
| `PUBLIC_URL` | Empty for now (the Railway address is used), or the client's own `https://` domain. See [Custom domain](#custom-domain). |
| `BRAND_NAME`, `BRAND_PHONE` | Shown to sellers and in the dashboard; the phone in the country's own format, however it is typed. |
| `OPERATOR_NAME`, `OPERATOR_EMAIL`, `OPERATOR_ADDRESS` | The business that receives the leads, for the privacy policy and the consent text. |
| `POLICY_EFFECTIVE_DATE` | The date the client's privacy policy takes effect. |
| `OWNER_PASSWORD` | The owner's first dashboard password, for one sign-in: the dashboard then asks for one of their own. |
| `TIMEZONE` | The owner's time zone, for dates and statistics. |
| `VAPID_SUBJECT` | `mailto:` the client's email. Push services use it to report problems. |
| `SOURCE_LABELS` | Names for every place besides the business card, printed (a QR code) or online (a link), e.g. `sticker:Car sticker,maps:Google Maps`. See [QR codes](#qr-codes). |

Leave `SECRET_KEY`, `VAPID_PUBLIC_KEY` and `VAPID_PRIVATE_KEY` empty: the
first deploy generates them and saves them into the file. Never change them
afterwards. A new `SECRET_KEY` signs the owner out; new VAPID keys switch
notifications off on every device.

The database, the bucket, `APP_ENV` and `STORAGE_BACKEND` are set by the
deploy script. Their values in the file only matter for local development.

## 2. Deploy

```bash
.venv/bin/python tools/deploy.py clients/acme.env
```

The script stops before creating anything if a setting would not start in
production, then:

1. creates the Railway project (named after `BRAND_NAME`, or
   `RAILWAY_PROJECT_NAME`) and saves its id into the file as
   `RAILWAY_PROJECT_ID`;
2. adds PostgreSQL with point-in-time recovery, the `photos` bucket and the
   `app` service. Without the backups it stops (see
   [Backups and restore](#backups-and-restore));
3. sets the app's variables. Database and bucket credentials are Railway
   references and never pass through your machine; secrets are sent over
   stdin and never printed;
4. sets the health check and a `*.up.railway.app` domain;
5. uploads and builds the current commit, exactly as committed, plus the
   client's brand files (see [Client branding](configuration.md#client-branding));
6. waits until `/healthz` reports this commit and the latest database
   migration, then prints the addresses and whether the backups are on.

It is safe to run again: existing resources are reused.

## 3. Set up the owner's phone

On the owner's iPhone, open `https://<address>/app` in **Safari**, tap
**Share → Add to Home Screen**, and open the app from the home screen
(iPhone only delivers notifications to home-screen apps). Sign in with
`OWNER_PASSWORD`, choose a password of your own when asked (nothing else opens
until then), turn on notifications, and send the test notification. On
Android, Chrome offers to install the app; then do the same. Leave the first
sign-in to the owner: whoever does it chooses the password.

Then submit a test lead through the form from another phone and check that the
notification arrives and opens the lead.

## Updating

**Installing for a client**, with no code changes of your own: move to the
newest release and run the same command again. There are no checks to run:
they need Node, Docker and gitleaks, which an installer does not.

```bash
git fetch --tags
git checkout "$(git tag --list 'v*' --sort=-v:refname | head -n 1)"
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python tools/deploy.py clients/acme.env
```

**Changed the code yourself**: commit it (the deploy uploads exactly the
checked-out commit) and run the checks before deploying:

```bash
tools/check.sh
.venv/bin/python tools/deploy.py clients/acme.env
```

Database migrations run before the new version starts serving; the old
version keeps answering until the new one is healthy.

## Hand over

The client owns the instance: their Railway account pays for it, and their
domain is on the cards. After the first deploy, in the Railway dashboard
(`railway open`): **Settings**, **Members**, invite the client's Railway email
as Editor; once they accept, **Transfer Ownership** to them (the three dots
next to their name). The client confirms by email within 24 hours; both
accounts need an active Hobby or Pro plan. The project keeps its id, so the
same settings file and command deploy updates as long as you stay on the
project as Editor (Editors can deploy and change settings, not delete).

## Custom domain

Required before any QR code or card: the commands refuse the
`*.up.railway.app` address, because a printed code points at one address for
good and it must be the business's own. Use a subdomain of the client's site
(`buy.example.com`), or a domain bought in the client's name.

1. Set `PUBLIC_URL=https://buy.example.com` in the client's file and deploy
   again. The script adds the domain and prints the DNS records to create at
   the client's domain registrar.
2. Wait until Railway shows the domain as active (`railway domain list
   --service app`) and the address opens with a valid certificate.
3. Owners who installed the app from the old address should install it again
   from the new one and turn notifications on there.

## QR codes

```bash
.venv/bin/python -m app.cli qr --env-file clients/acme.env                             # business card
.venv/bin/python -m app.cli qr --env-file clients/acme.env --source sticker            # any printed place
.venv/bin/python -m app.cli qr --env-file clients/acme.env --source maps --link-only   # an online place
```

This writes `qr/<domain>-<source>.svg` for the print shop and a `.png`
preview; `--link-only` prints the link and writes nothing, for a map listing,
a social profile or an auto-reply. The address comes from the file's
`PUBLIC_URL` (`--url` overrides it) and the place names from its
`SOURCE_LABELS`: a label the file does not name is flagged, since the
dashboard would show it as Other. Business card codes point at `/v`, which
labels the lead "Business Card"; every other place uses `/?src=<source>`, so
statistics count each one apart. The command uses error correction H and the
standard quiet zone, and refuses a code whose modules would print smaller
than 0.4 mm at the card size (20 mm by default, `--size-mm` to change). Tell
the designer not to crop the white margin around the code.

## Business card

A ready card in the client's color and logo, with the card QR code:

```bash
.venv/bin/python -m app.cli card --env-file clients/acme.env --name "Mike"
```

It writes, into `cards/`:

- `<brand>.pdf`: the file for the print shop, in the size shops in the
  client's country use (`CARD_SIZE`, or `--size`): US 3.5 x 2 in with a
  0.125 in bleed (3.75 x 2.25 in pages), Russia 90 x 50 mm with 2 mm (94 x 54
  mm), Europe 85 x 55 mm with 3 mm (91 x 61 mm), or any card from 85 x 50 to
  92 x 56 mm with 3 mm, such as Japan's 91 x 55 mm; TrimBox and BleedBox set.
  Text in a script the card's font lacks (Chinese, Korean, Greek...) is set in
  `CARD_FONT`; a card with a letter no font has, or in a script whose letters
  join (Arabic, Hebrew, Hindi, Thai), is refused with a message saying so. Vector, CMYK only, fonts embedded. The QR code is in black ink only
  on unprinted white; small gray text is black ink only; the rich black
  background stays well under 300% total ink; black on the accent overprints.
  No text is under 7 pt or closer than 0.2 in to the trim line.
- `<brand>-crop-marks.pdf`: the same with crop marks, for shops that ask.
- `<brand>-preview.png`: both sides as they look after trimming.

The address comes from `PUBLIC_URL` (or `--url`), the phone from
`BRAND_PHONE` (or `--phone`), and `--name` adds a contact person. The accent
is converted from `BRAND_COLOR`; if the business has official CMYK values
for its color (brand guide, earlier print jobs), pass them, e.g.
`--cmyk 0,45,100,0`. The wording is in `locales/en.json` under `card`; text
that would have to print under 7 pt is refused with the key to shorten.
Bright screen colors print a little duller: order a proof and scan its code
before a full run.

## Backups and restore

PostgreSQL has point-in-time recovery: Railway archives the database
continuously. Every deploy turns it on if it is off, and the last lines
of every deploy say which state it is in (`backups: on (...)` or `OFF`).

The deploy stops when the backups cannot be turned on, or when their state
cannot be read, and says what to do: update the Railway CLI
(`railway upgrade --yes`), or turn them on in Railway (the Postgres service,
**Backups**, **Enable PITR**), then deploy again. `--no-backups` deploys
without them, for a business that agrees to start that way, and the summary
then shows **Backups are OFF** in a banner. A later deploy without the flag
stops again until they are on; the flag itself never turns backups off.

Railway can restore the database to any minute into a **new** service:

```bash
railway postgres pitr status --service Postgres
railway postgres pitr restore --service Postgres --at 2026-10-05T14:55:00Z --new-service-name postgres-restored --yes
```

Check the restored data first. The deploy script always points the app at
the service named `Postgres`, so to switch, rename the old database service in
Railway, give the restored one the name `Postgres`, and deploy again (this
switch has not been rehearsed yet: do it calmly, not for the first time in an
emergency). Delete the old database only after living on the new one for a
few days, and delete any restored copy you do not use: retention does not
reach it, so a forgotten copy keeps personal data past the 90 days. Deleting a
service does not delete its volume; check `railway volume list`.

Railway does not back up buckets. Photos are working material that retention
erases anyway; losing them loses no lead.
