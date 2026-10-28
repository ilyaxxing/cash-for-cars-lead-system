# Setting up the system for a business: a guide for Claude Code

This file is written for the AI assistant. A person gave you this repository
because they want the lead system running for a business that buys used cars:
often a client they found, sometimes their own business. Usually they are not
technical. Lead them from the first question to a working system on the
business owner's phone, and do the technical work yourself.

What they get at the end: a web form for car sellers (opened from a QR code on
a business card), a dashboard for the owner that installs on the phone like an
app, and a push notification on that phone for every new lead.

## How to work with the person

- Speak the person's language: the one they write to you in. The product's
  language follows the business's country: English for the US, the sellers'
  language elsewhere ([Another country](#another-country)).
- One step at a time. Say in a sentence what you are about to do and why, then
  do it. Ask a few questions at once at most, never a long questionnaire.
- Run every command yourself. Ask the person only for what only they can do:
  facts about the business, signing in to Railway in the browser, payment,
  testing on a phone, DNS settings at a domain registrar, handing the project
  over in the Railway dashboard.
- Use plain words: "server", "address", "password", "settings file". Avoid
  "env vars", "VAPID", "PITR" and the like; if a term can't be avoided, explain
  it the first time.
- Before anything that costs money (creating the Railway project, buying a
  domain), say what it costs and wait for a clear yes.
- The client's settings file holds passwords and keys. Never paste its contents
  into the chat, never commit it, never send it anywhere: only the deploy
  script reads it. The one exception is the owner's password, which you show
  when handing over.
- Never push to GitHub. Change tracked files only as described in
  [Customizing the form](#customizing-the-form).
- When something fails, read the error, fix what you can, and tell the person
  in a sentence or two what happened. Never hide a failure.

## Before you start

First ask where the business is: its country, and the language its sellers
speak. The steps below are written for the US. For any other country, read
[Another country](#another-country) now, go through its first part before
step 1 (it can change where the system runs, and it says what the system
cannot do there yet), and follow its notes as you go: the system adapts to
the language, the form, the privacy law, the card and, where needed, the
server, without changing its code.

Tell the person briefly what they will need:

1. This computer (macOS, Windows or Linux), for about an hour the first time.
2. Facts about the business (asked in step 3); they can ask the client as you go.
3. Two Railway accounts, each on the Hobby plan ($5 a month, with a payment
   card): their own, where the instance is built and tested, and the
   business's own, on the business's card, which the finished project is
   handed over to (step 10). Hosting is about $5 a month (Railway Hobby,
   includes $5 of usage; not yet checked against a real client's bill).
   Railway moves a project between accounts only when both have a paid plan.
   Outside the US the instance may run on a server of the business's own in
   its country instead ([Another country](#another-country)).
4. The business's own domain, owned by the business: a subdomain of its
   website such as `buy.<domain>`, or a new domain the business buys in its
   own name (about $10-15 a year). QR codes and cards are made only for it.
5. Later: the owner's phone (iPhone or Android) for ten minutes.

Explain why the Railway account and the domain belong to the business: printed
cards point at the domain for good, and the database holds sellers' personal
data, with the business named as its operator in the privacy policy. Whatever
happens between the person and the business later, everything keeps working.

## Step 1. Tools and code

Check what is installed and install what is missing (ask first):

- **git**: `git --version`. On macOS, `xcode-select --install` provides it.
- **Python 3.12**: `python3.12 --version` (Windows: `py -3.12 --version`).
  macOS: `brew install python@3.12`; Windows: `winget install Python.Python.3.12`;
  Linux: the distribution's package or python.org.
- **Railway CLI**: `railway --version`. macOS: `brew install railway`; with
  Node.js on any system: `npm install -g @railway/cli`; macOS/Linux without
  either: `bash <(curl -fsSL cli.new)`.

If you are not inside this repository yet, clone it into a folder of its own,
for example `~/car-buyout`, and work from there. Deploy the newest release
(a `v*` tag), not `main`: `main` is where development happens.

```bash
git clone https://github.com/ilyaxxing/cash-for-cars-lead-system.git ~/car-buyout
cd ~/car-buyout
git checkout "$(git tag --list 'v*' --sort=-v:refname | head -n 1)"
```

Then the Python environment (Windows: `.venv\Scripts\python` instead of
`.venv/bin/python` here and below):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Node.js and Docker are not needed: Railway builds everything.

## Step 2. Railway accounts

On a server of the business's own instead of Railway: the server and SSH
access, as in [Another country](#another-country), replace this step.

**The person's own account**, where the instance is built:

- No account yet: send the person to https://railway.com to sign up, then to
  add a payment method (Hobby plan) in the account's billing settings. Wait
  until they confirm.
- Sign the CLI in with `railway login`. It opens the browser. If it can't run
  from your shell, ask the person to type `! railway login` in Claude Code (the
  `!` runs it in their own terminal) and finish in the browser.
- Check with `railway whoami`. If it lists more than one workspace, ask which
  one to build in; it goes into `RAILWAY_WORKSPACE`.

**The business's own account**, which the project is handed over to in step
10: ask the person to have the business sign up at https://railway.com with
the business's email and add the business's payment card (Hobby plan), and to
tell you the email it signed up with. It can wait until step 10, but asking
now saves time: the business has to accept the hand-over, which can take a
day.

## Step 3. Questions about the business

Ask in small groups, offer sensible defaults, and note the answers. The names in
brackets are the settings they fill in step 4.

**What sellers see**
- The business name as sellers should see it, e.g. "Lone Star Car Buyers"
  (`BRAND_NAME`).
- A business phone for the privacy policy, optional (`BRAND_PHONE`).
- Where the business is, to pick its time zone, e.g. Texas → `America/Chicago`
  (`TIMEZONE`). Confirm the zone with the person.
- How sellers may ask to be contacted: phone call, SMS, WhatsApp and email
  out of the box. Telegram can be added, for example when many of the
  business's sellers speak Russian; if they want it, add it to the preset as
  in [Customizing the form](#customizing-the-form);
  [docs/customize-the-form.md](docs/customize-the-form.md) shows the line.
  Keep the rest as it is.

**The look**

Out of the box the system has a finished look: a lime-green accent, a
price-tag mark next to the business name, and a car photo on the first
screen of the form. Say so in a sentence, then ask about one item at a time,
"keep it or change it?". Keeping is always a fine answer, and whatever is not
changed stays as it is.

If anything changes, pick the business's id now (lowercase with dashes, e.g.
`lone-star-car-buyers`; step 4 uses the same one). Files go into
`clients/<id>/`, which git ignores. The person can drop a file into the chat
or say where it is (Downloads, Desktop); copy it into the folder yourself.

1. **Color** (`BRAND_COLOR`). Keep the lime green, or use the business's
   color? They can name it, give a code like `#FF8A00`, or send a picture of
   their sign, website or logo: then pick its main color, and say which code
   you picked. The screens are dark, so a dark color (navy, black) is refused
   by the deploy's check, which suggests a lighter shade of it; offer that.
2. **Logo** (`BRAND_LOGO`). Keep the price-tag mark with the business name,
   or use their logo? If their own: ask for the logo file, the version for
   dark backgrounds (white or light lettering) on a transparent background,
   as PNG. A logo on a solid background of its own (PNG or JPEG) works too and
   shows as a box. A phone photo of a sign is not a logo file: ask for the
   file from whoever made the logo, or the one on their website. Save it as
   `clients/<id>/logo.png`. If the logo exists only as SVG or PDF and a
   converter is at hand (e.g. `rsvg-convert`), make a PNG at least 800 px
   wide; otherwise ask for a PNG.
   No file, but they can describe it? Then you may draw a simple one: the
   name in the bundled fonts (`app/branding/fonts/`) and at most one simple
   shape, light on a transparent background, PNG, at least 800 px wide. Show
   it to the person, change it until they like it, and use it only after a
   clear yes. Never imitate another company's logo.
3. **Home-screen icon** (`BRAND_ICON`). Only if they gave a logo. A roughly
   square logo becomes the phone's app icon by itself; a wide one does not,
   and the price tag in their color is used instead. If they have a square
   version of the logo, at least 512 x 512 px, save it as
   `clients/<id>/icon.png`.
4. **Welcome photo** (`BRAND_PHOTO`). Keep the car photo on the first
   screen, or use their own? Theirs must be a landscape photo at least
   1200 px wide that the business has the rights to: their lot, a car they
   bought. No readable license plates, no customers' faces. Save it in
   `clients/<id>/`, e.g. `photo.jpg`.

The business card is asked about later, in step 9.

**Privacy policy** (the business is responsible for sellers' data)
- The company's legal name, e.g. "Lone Star Car Buyers LLC" (`OPERATOR_NAME`).
- An email for privacy requests (`OPERATOR_EMAIL`).
- A mailing address, optional (`OPERATOR_ADDRESS`).
- The date the policy takes effect: today unless they say otherwise
  (`POLICY_EFFECTIVE_DATE`, `YYYY-MM-DD`).

Tell them the privacy policy is a template, not legal advice: the business
should have its lawyer read it at `/privacy` before launch.

**Where the QR codes will be**
- The business card is built in. Ask about other places: a sticker on the lot,
  flyers, an ad. Each gets a short id and a name, e.g.
  `parking:Parking lot,flyer:Flyers` (`SOURCE_LABELS`), so statistics show
  which places bring sellers.

**Address**
- Which domain will the cards use? If the business has a website, a
  subdomain of it such as `buy.example.com` costs nothing. If not, it buys one
  in its own name (about $10-15 a year). The first deploy runs on the Railway
  address; the domain is connected in step 8, before anything is printed.

**Owner's password**
- Generate a strong, typeable one (three random words and a number) unless the
  person wants to choose it (`OWNER_PASSWORD`). The owner can change it later
  in the dashboard.

**Photo storage location**
- West of the Rockies: `sjc`; otherwise `iad` (`RAILWAY_BUCKET_REGION`). It
  can't be changed later.

## Step 4. The settings file

1. The id from step 3, or pick one now: lowercase with dashes, e.g.
   `lone-star-car-buyers`.
2. `mkdir -p clients && cp .env.example clients/<id>.env`, then edit the file
   with your file tools and fill in the answers from step 3.
3. The look from step 3: `BRAND_COLOR`, and the files as paths from the
   repository, e.g. `BRAND_LOGO=clients/<id>/logo.png`. Leave empty whatever
   they keep.
4. Leave these empty: `PUBLIC_URL` (unless the domain is already set up),
   `SECRET_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `RAILWAY_PROJECT_ID`.
   The deploy script generates the keys, writes them into the file, and adds
   the project id after the first run. Local-only values copied from
   `.env.example` (database, storage) are ignored on Railway.
5. Show the person a short summary of what you filled in (names, email, time
   zone, sources, what changes in the look; not the password) and ask them to
   confirm.
6. Tell them: `clients/` never goes to GitHub, and this file is the only key to
   this business's installation. They should keep a copy in a password
   manager, together with the logo and photo files.

## Step 5. Deploy

On a server of the business's own: `.venv/bin/python tools/deploy_vps.py
clients/<id>.env` instead, once the domain points at the server (step 8
comes first there); the rest of this step reads the same.

Ask for the go-ahead: this creates the Railway project on the person's own
account; it moves to the business's account in step 10. Then:

```bash
.venv/bin/python tools/deploy.py clients/<id>.env
```

The first run takes 5-10 minutes. The script checks the settings before it
creates anything and says exactly what is wrong; fix the file and run it again.
It creates the database (with continuous backups), photo storage and the app,
uploads the code together with the logo and photo files, and waits until the
new version answers. It is safe to run again at any time. A logo or photo
that would look broken (a dark logo, a small or portrait photo) stops it
before anything is created, with a message saying what to ask the client for.

At the end it prints three addresses: the seller form, the business card link
(`/v`) and the dashboard (`/app`). Note them for the person.

If it stops: read its message; `railway logs --service app` shows the app's own
log. The script never prints secrets, so you can show its output.

## Step 6. Test it together

1. Ask the person to open the seller form on their own phone and send a test
   car (any car; a 555 number like 512-555-0100 is fine).
2. Open the dashboard on the computer, sign in with the owner's password, and
   check that the lead is there with its photos.
3. Mark the test lead Rejected so it doesn't count as a real one.
4. Ask whether the look is right: color, logo, the first screen's photo.
   Anything to change: update the settings file or the files in
   `clients/<id>/` and deploy again.

## Step 7. The owner's phone

Give the person this message for the business owner, filled in, in the
owner's language (English in the US; elsewhere translate it, as the
dashboard's texts are):

> Your new lead system is ready. To get a notification for every car seller:
>
> 1. On your iPhone, open **Safari** and go to <dashboard address>.
>    (Android: open it in **Chrome** and tap **Install app**.)
> 2. Tap **Share**, then **Add to Home Screen**, then **Add**.
> 3. Open the new icon on your home screen and sign in with the password:
>    <password>
> 4. Tap **Turn on notifications** and allow them, then **Send test
>    notification**.
>
> iPhone shows notifications only for the home-screen app, and needs iOS 16.4
> or newer. Make sure Focus or Do Not Disturb isn't hiding them.

Then ask the person to send another test lead and confirm the owner got the
notification. If it didn't arrive, see [Troubleshooting](#troubleshooting).

## Step 8. The business's own domain

Required: the QR and card commands refuse the Railway address. Explain why: a
code printed on cards points to one address for good, so it must be the
business's own, not the Railway one, which belongs to one Railway project.

1. If the business has a domain, use a subdomain such as `buy.<domain>`. If
   not, the business buys one in its own name (for example at Cloudflare or
   Namecheap, about $10-15 a year); ask before anyone pays.
2. Set `PUBLIC_URL=https://buy.<domain>` in the settings file and run the deploy
   again. It prints the DNS records to add at the registrar.
3. Walk the person, or the business's web person, through adding them at the
   registrar. Check `railway domain list --service app` until the domain is
   active, then open the address and confirm the padlock (certificate) shows.
4. The owner opens the dashboard at the new address and does step 7 again:
   notifications belong to the address they were turned on at.

## Step 9. Business card and QR codes

Do this after step 8: the commands make codes only for the business's own
domain.

**Business card.** These cards are mostly left under the windshield wipers
of parked cars, so they are printed by the thousand. Ask whether they want
the ready card: on the front the brand, a headline, what they buy and the QR
code; on the back a promise, three lines about what they buy, the same QR
code, and the contact person and phone; all in their color, in the size
print shops in their country use (`CARD_SIZE`). If they have their own
designer, skip to the QR codes below and give the designer the SVG.

Make it once as it is:

```bash
.venv/bin/python -m app.cli card --env-file clients/<id>.env
```

Open `cards/<brand>-preview.png` for the person to look at (macOS: `open`,
Windows: `start`, Linux: `xdg-open`). Then go through the design with them,
one item at a time: say what is there now and ask whether to change it.

1. The headline, two lines, the first in the accent color (`card.front_hot`,
   `card.front_rest`), e.g. "We buy / any car".
2. The three short tags under it (`card.front_tag_1` to `card.front_tag_3`).
3. The call to action under the code and the hint below it (`card.cta`,
   `card.scan`).
4. The promise on the back, two lines (`card.back_title_1`,
   `card.back_title_2`), and its three lines with check marks
   (`card.back_list_1` to `card.back_list_3`).
5. The contact: whose name goes on it, if anyone's (`--name "<name>"`), and
   the phone (`BRAND_PHONE`, or `--phone`).
6. The color. If the business has official print values for it (CMYK, from a
   brand guide or an earlier print job), pass them as `--cmyk C,M,Y,K`;
   otherwise the screen color is converted.
7. The logo (`BRAND_LOGO`) and the card size (`CARD_SIZE`).

Wording goes into the client's own texts file, `clients/<id>/texts.json`
(`LOCALE_FILE`), with only the keys that change under `card`, never into
`locales/` (see [Customizing the form](#customizing-the-form)). After each
answer, make the card again with the same options and show the new preview.
If a text is too long to print legibly, the command says which one to
shorten. The layout itself (where things sit, the fonts, the code's size) is
the same for every client: it is what keeps the card print-ready. A business
that wants a different layout gives its designer the QR code SVG below.

For printing, tell the person:
- Send `cards/<brand>.pdf` to the print shop. It is print-ready: the size
  shops in the client's country use (`CARD_SIZE`: US 3.5 x 2 in, Russia
  90 x 50 mm, Europe 85 x 55 mm, or the size given) with their bleed added, CMYK, fonts
  embedded. If the shop asks for crop marks, send
  `cards/<brand>-crop-marks.pdf` instead.
- Choose a matte or uncoated stock if the owner will write on the cards.
- Screen colors print a little duller. Order a proof first and scan its
  QR code with a phone before the full run.

**QR codes** for anything else (a sticker on the lot, flyers):

```bash
.venv/bin/python -m app.cli qr --url https://buy.<domain>
.venv/bin/python -m app.cli qr --url https://buy.<domain> --source parking
```

The files land in `qr/`: the `.svg` is for the printer, the `.png` for a quick
look. Tell the person: send the SVG to the print shop, ask them not to crop the
white margin around the code, and scan a printed proof before ordering a batch.
If the command refuses (the code would print too small), it says why: print it
larger with `--size-mm` or use a shorter address.

## Step 10. Hand over

On a server of the business's own there is nothing to transfer: the business
owns the server and the domain, and the person's SSH key is the way in. With
a support plan it stays; without one, the business removes it in the
provider's panel. Skip to the summary below.

**Hand the project to the business's Railway account.** The person does this
in the browser; guide them one click at a time:

1. Open the project with `railway open`, then **Settings**, **Members**.
2. Invite the email the business signed up with (step 2) as **Editor**, and
   ask the business to accept the invitation.
3. Click the three dots next to the business, then **Transfer Ownership**.
   The business confirms in an email within 24 hours; both accounts must
   have an active Hobby or Pro plan.
4. Once it is confirmed, the business is the owner and Railway bills its
   card. Check **Members**: with a support plan, the person stays on the
   project as Editor, enough to deploy updates with the same command (the
   project keeps its id, `RAILWAY_PROJECT_ID`). Without one, the business can
   remove them.

The settings file stays with whoever supports the system: updates need its
keys. If the business moves support to someone else, it goes to them over a
private channel (a password manager's shared item, not email or chat).

Then summarize for the person, in their language: the three addresses, where
the settings file is, the monthly cost (the business's Railway plan and
domain), and that you are done. Give them a short note for the owner, in
the owner's language (English in the US):

- The form address, the business card link and the dashboard address.
- Statuses: New (not handled yet), In Progress (talking or negotiating),
  Purchased (bought the car, counts in statistics), Rejected (passed).
- Privacy: a seller's name, phone, email and photos are erased automatically
  90 days after the lead is marked Purchased or Rejected. Leads never closed
  are never erased, so close them when done.
- The password can be changed in Settings; if it is forgotten, the person who
  installed the system can reset it.

And remind the person:
- Updates: move to the newest release (`git fetch --tags`, then
  `git checkout` the newest `v*` tag), then the same deploy command, while
  they are an Editor on the business's project (docs/deploy.md, Updating).
- Forgotten owner password: change `OWNER_PASSWORD` in the settings file and
  deploy again; that resets it.
- Backups: Railway keeps about 4 weeks of continuous database backups
  (point-in-time recovery). Photos are not backed up, which is fine: they are
  working material that is erased anyway. On a server of the business's own,
  the dumps sit on that server: keep a copy off it (docs/deploy-vps.md).
- Changing the look later: change the settings file or the files in
  `clients/<id>/`, then deploy again. A phone keeps the app icon it was added
  with: to see a new icon, remove the app from the home screen and add it
  again (then turn notifications on again).

## Another country

The system fits a business in any country without changing its code: its
language, its form, its privacy policy, its card and, where needed, where it
runs. Everything country-specific goes into the business's own files in
`clients/<id>/`, next to its settings, never into `presets/` or `locales/`:
then a new release applies to every client without conflicts.

Go through the list below for the business's country. For each point, use
what you know and look up what you are not sure of (a web search, when you
have one): the country's rules change, and a wrong guess ends up printed on
a thousand cards. Tell the person what you found in a sentence or two and
let them confirm it with the business. Russia is the worked example
throughout.

**First, what decides the plan** (before step 1):

1. **What the system cannot do there yet.** Say it at once, before anyone
   pays for anything:
   - Languages written right to left (Arabic, Hebrew, Persian, Urdu): the
     form and the dashboard are laid out left to right only. Offer English,
     or a language the sellers also read, if that works for the business.
   - On the card, scripts whose letters join or change order (Arabic,
     Hebrew, Hindi and the other Indian scripts, Thai): the card command
     refuses them. The form and the dashboard show them, but the card's
     texts must be in another script, or the print shop sets the card from
     the QR code (step 9).
   - One language per instance: the one most sellers read.
   - The chat button in a lead opens WhatsApp, or Telegram for a seller who
     chose it. Where sellers use another messenger (WeChat in China, LINE in
     Japan and Thailand, KakaoTalk in Korea, Viber in some countries), it can
     be added as a contact method the seller picks; the owner then reaches
     them by the phone number, and the WhatsApp button stays.
   - Notifications reach the owner through the phone maker's push service:
     an iPhone, or an Android phone with Google's services (in mainland
     China, usually an iPhone).
2. **Where the data may be kept.** Look up the country's personal data law:
   whether sellers' names and phones must stay in the country, whether
   keeping them abroad needs extra paperwork, and whether the business must
   register with a regulator. Russia's 152-FZ keeps them in Russia. When the
   law keeps them at home, or you are not sure, choose a server in the
   country (below).
3. **Whether a site needs a permit there.** Some countries require one
   before a server in the country may serve a site (mainland China's ICP
   filing takes weeks). Find out before promising a launch date.
4. **Whether the business can pay Railway**: its country's cards may be
   refused. Then a server of its own.
5. **The domain.** Any domain the business owns works. Some country domains
   ask for documents (look it up); a `.com` never does.

**Where it runs.** Railway, as in the steps above, unless points 2-4 say
otherwise; then a server of the business's own, in its country, with
`tools/deploy_vps.py` ([docs/deploy-vps.md](docs/deploy-vps.md)).

For a server of its own, the business rents it in its own name from a
provider in its country: Ubuntu 24.04, 2 GB of memory, 20 GB of disk, a
public IPv4 address. Give the person this computer's SSH public key
(`~/.ssh/id_ed25519.pub`; make one with `ssh-keygen -t ed25519` if there is
none) to add when the server is created, or run `! ssh-copy-id
root@<address>` with them once, with the root password from the provider.
Then `VPS_HOST=root@<address>` in the settings file. The domain gets an A
record pointing at the server's address before the first deploy (step 8
moves before step 5). Where Docker Hub is slow or closed, set
`DOCKER_MIRROR` (the provider's mirror, or `https://mirror.gcr.io`). The
daily dumps stay on that same server: have the business turn on the
provider's server backups if it offers them, or copy a dump off now and then
([docs/deploy-vps.md](docs/deploy-vps.md#logs-backups-restore)).

**Then the details** (with step 3):

- **Language**: `LOCALE`, the language's code, with its script where it is
  written in more than one: `ru`, `sv`, `tr`, `ja`, `zh-Hans` (simplified
  Chinese) or `zh-Hant` (traditional). Never the country (`zh-CN` is
  refused): that comes from the form.
- **Phone numbers**: the country's code in the form (`phone_region`, e.g.
  `RU`). Numbers from other countries are refused, as US numbers are in the
  US.
- **Postal code**: its pattern in the form (`postal_code_pattern`, e.g.
  `'\d{6}'` in Russia, `'\d{3} ?\d{2}'` in Sweden), or the field dropped
  where the country has none.
- **Distance**: kilometers or miles (`distance_unit`).
- **Currency** (`CURRENCY`, e.g. `RUB`), written the country's way by
  itself. Where a car costs millions (Korean won, Vietnamese dong,
  Indonesian rupiah), raise the price question's `max` in the form to a
  generous price in that currency: the field takes as many digits as that.
- **Time zone** (`TIMEZONE`, e.g. `Europe/Moscow`): the business's own.
- **The form's questions.** Offer the US questions, translated, and ask what
  to add, drop or change: in Russia, for example, the vehicle title (ПТС,
  original or duplicate), the number of owners, and whether the car is
  pledged (залог). Car makes common there go into the make suggestions.
- **How sellers like to be reached**: in Russia Telegram is common, so add
  it to the contact methods (see point 1 for others).
- **The card's size** print shops there use (`CARD_SIZE`): `3.5x2in` in the
  US and Canada, `90x50mm` in Russia, `85x55mm` in most of Europe, or any
  card from `85x50mm` to `92x56mm` (Japan's `91x55mm`, China's `90x54mm`).
  Look it up for other countries.
- **The card's font.** The card's own font has Latin and Cyrillic letters.
  For Chinese, Japanese, Korean, Greek and other scripts, `CARD_FONT` names
  a font that has them: with the person's OK, download the static Bold
  `.ttf` of the right Noto font from Google Fonts (Noto Sans SC, TC, JP or
  KR, or Noto Sans; free to use) into `clients/<id>/`. The form and the
  dashboard need nothing: phones show those scripts in their own fonts.

**The business's files** (with step 4), in `clients/<id>/`:

1. `form.yaml` (`PRESET_FILE`): a copy of `presets/us-car-buyout.yaml` with
   its own `id` (e.g. `ru-car-buyout`), `distance_unit`, `phone_region` and
   `postal_code_pattern` instead of `postal_code_format`, and the changes
   agreed above.
2. `texts.json` (`LOCALE_FILE`): the whole of `locales/en.json` in the
   sellers' language. Every key, with `{placeholders}` exactly as they are;
   US details made local (the phone placeholder in the local format, "ZIP
   code" in the local term, the card's texts under `card`); texts for any new
   question. Short and natural, in the same tone: read it back as a seller
   would. A placeholder gets its word or date as it is, in one form, and a
   counted text has only English's one and many: word them so they read
   right anyway (in Russian "Источник: {source}", not a sentence that would
   need the word declined). Then run `.venv/bin/python -m app.cli check-texts --env-file
   clients/<id>.env`: it lists every text still missing (it would show as its
   key on screen) and every placeholder that differs from English.
3. `policy.md` (`PRIVACY_POLICY_FILE`): the privacy policy in that language
   and under that country's law, built from `locales/privacy-policy.en.md`
   with its `{placeholders}` kept: the operator and its contact, what is
   collected and why, the legal basis (the seller's consent), where the data
   is stored, how long (90 days after a lead is closed), and the seller's
   rights and how to use them, in the terms of that law (in Russia, 152-FZ,
   storage in Russia). Tell the person plainly that it is a draft for the
   business's lawyer to review before launch, along with any registration
   with the regulator (in Russia, notifying Roskomnadzor).
4. In the settings file: `LOCALE`, `LOCALE_FILE`, `PRESET_FILE`,
   `PRIVACY_POLICY_FILE`, `CURRENCY`, `TIMEZONE`, `CARD_SIZE`, `CARD_FONT`
   if needed; and on a server of its own `VPS_HOST` and `PUBLIC_URL` (the
   domain, required there).

The deploy script checks all of it before uploading and names any missing
text or wrong field; the card command refuses a letter no font has. After
the deploy, go through the form once on a phone with the person, in the
sellers' language, and fix in `texts.json` whatever reads wrong before the
owner sees it.

## Customizing the form

Only if the business asks for different questions or wording. A client's
changes go into its own files next to its settings, never into `presets/` or
`locales/`: then a new release applies without conflicts, for every
client.

- Wording (the form's, the dashboard's, the card's): `clients/<id>/texts.json`
  with only the keys that change, e.g.
  `{"card": {"front_hot": "We pay cash"}}`, and
  `LOCALE_FILE=clients/<id>/texts.json` in the settings file. The keys are the
  ones in `locales/en.json`.
- Questions: copy `presets/us-car-buyout.yaml` to `clients/<id>/form.yaml`,
  change it, set `PRESET_FILE=clients/<id>/form.yaml`, and add the texts for
  any new question to the texts file.

[docs/customize-the-form.md](docs/customize-the-form.md) explains both
formats; a new question needs no database change. The deploy script checks
the files before it uploads anything and says which text or field is wrong.

## Troubleshooting

- **"The settings would not start in production"**: the message lists what is
  missing or malformed. Fix the settings file and run the deploy again.
- **"The git tree has uncommitted or untracked files"**: undo stray edits: a
  client's changes belong in `clients/<id>/`, never in tracked files. Files in
  `clients/` and `qr/` are ignored and never cause this.
- **The deploy waits and then times out**: `railway logs --service app` shows
  why the app didn't start.
- **Railway refuses with "Deploys have been paused" or the CLI cannot reach
  it**: check https://status.railway.com. During an outage nothing is created
  or charged; tell the person, and run the deploy again once Railway reports
  builds working. The script picks up where it stopped.
- **No notification on the iPhone**: the app must be opened from the home
  screen, iOS 16.4+, Focus off. In the dashboard: Settings → Notifications,
  switch off and on, then send a test. The red banner on the Leads page appears
  when no device can receive notifications.
- **A forgotten owner password**: see step 10.
- **"A brand file would not work"**: the message names the file and what is
  wrong with it (too dark for the dark screens, too small, not landscape).
  Ask the client for a better file, or leave that setting empty to keep the
  default.
- **Several businesses**: one settings file, one `clients/<id>/` folder and
  one Railway project each; run the deploy with the right file.
