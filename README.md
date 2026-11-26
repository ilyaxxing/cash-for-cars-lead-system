https://github.com/user-attachments/assets/00f612b1-88cf-4440-9f57-99ad354605b9

**[Try the live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/)**

# Cash for Cars Lead System

**Set up a branded lead system for local car buyers, and charge for the setup.**

Business #1 of **100 Ready-to-Launch Businesses**: open source, free to copy,
yours to sell. By [@ilyaxxing](https://instagram.com/ilyaxxing).

Give a car buyer QR codes and links for their cards, signs and online
listings. Sellers send their car through a short form, and the buyer gets a
push on their phone in seconds, with every lead in one app. In Statistics,
the buyer can add a source, copy its seller link and save its QR code for sharing or print.

Suggested price: $300–600 per setup, plus optional monthly support. The
business pays its own hosting and domain.

[Live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/) ·
[Set it up with Claude Code or Codex](#get-started) · [Business model](docs/business.md)

## How it works

1. **QR codes and links.** A seller scans a code or opens a link wherever
   they see it: a card under a wiper (it comes as a print-ready file in the
   buyer's color, with their logo; some cities and private parking lots ban
   this, so the client checks the local rules), a sticker on the buyer's own
   car, a poster at a partner repair shop, a sign or banner, a link in the
   Google Maps listing, and more ([every place](docs/business.md#where-leads-come-from)).
   Each place gets its own code or link, so statistics tell them apart.
2. **The seller's form.** Three short steps about the car, then the
   seller's contacts: that is already a lead. History, price and photos
   follow, all optional. No app, no account.
3. **A notification to the buyer** on their iPhone or Android, usually within
   seconds.
4. **The app.** Leads by status, photos, one tap to call, and statistics on
   which places bring cars.

## The business

**Who buys it:** cash-for-cars buyers, junk and salvage car buyers, small used
car lots and independent dealers. The best client already hands out cards or
puts up signs. **Where to find them:** "We buy cars" cards under wipers and
road signs, Google Maps, Facebook Marketplace and local groups, tow companies
and repair shops.

| | Price | What's included |
|---|---|---|
| Setup | $300-600 once | Turnkey: installation, their name, color and logo, connecting their domain, the app on the owner's phone, the card PDF, and QR codes and links for every place |
| Support | $25-50 a month | Optional: up to two small changes a month (form questions or interface texts), updates to new releases, a reply within a working day. New features and rework are extra. |
| Hosting | Railway from $5 a month, or the server provider's rate | Paid by the client |
| Domain | about $10-15 a year | In the business's name, if it has none |

Hosting, the domain and printing are paid by the client directly, on top of the setup price.

Railway hosting is from $5 a month (Railway Hobby includes $5 of usage; anything above is billed, taxes may apply).
Check the bill after the first week.

You pick the price, and whether to sell the setup alone or with monthly
support. More in [docs/business.md](docs/business.md).

**Find the first client.** [Getting your first client](docs/first-client.md):
where to look, the first message, answers to the questions car buyers ask,
and how to offer the setup.

**Show it to a client.** [The page for car buyers](https://car-buyer-demo.github.io/)
has the same live demo and what it does for their business, without prices,
setup details or GitHub. Send it in their name and color: add them to the link
(`https://car-buyer-demo.github.io/?name=Rapid+Cash+Cars&color=ff8a00`), or make it with the link
maker on the [project page](https://ilyaxxing.github.io/cash-for-cars-lead-system/#show), which
also picks the buyer's country and language: eleven of them, as in [countries/](countries/).

## Get started

Choose an assistant and open an empty local folder on a Mac or Linux
computer (on Windows, use WSL).

- **Claude Code** — open the Code tab in the Claude desktop app or start
  [Claude Code](https://claude.com/product/claude-code) in the folder.
- **ChatGPT / Codex** — open a local project in Codex with access to the
  folder and its terminal. In the ChatGPT desktop app, choose Codex and
  [work locally](https://learn.chatgpt.com/docs/environments/modes).
  To continue in a new chat, reopen
  the cloned repository folder and ask Codex to resume the installation.

Send the same request in either:

```text
Set up https://github.com/ilyaxxing/cash-for-cars-lead-system for my client.
```

The assistant asks about the business, sets up the system and guides you
through a test on the owner's phone. You sign in and approve the hosting
cost before it creates the server. It then helps connect the domain and
makes the card and QR codes. About an hour for the setup
itself once the accounts are ready; handing the project over to the business
and the domain's DNS can take up to a day.

- **You bring** access to Codex or to Claude Code (Claude Pro or higher,
  or an Anthropic API account). For Railway setups you also need your own [Railway](https://railway.com)
  account on the Hobby plan, from $5 a month (usage above the included $5 is
  billed): each project is built there before it is handed over.
- **The business brings** its domain, its name and email, and the owner's phone
  for ten minutes. For a Railway setup it also needs its own account and payment
  card to take over the project, with hosting from $5 a month.

<details>
<summary><b>Other countries</b></summary>

The system can be adapted for other countries: the assistant changes the sellers'
language, the questions, the privacy policy, the card's size and, where
needed, where it runs. If local hosting is required, use a server in the
business's country. The legal side needs a local check: where sellers'
data may be kept, whether it may leave the country and what the business
must register are for its local lawyer to confirm. For the countries in
[countries/](countries/) it starts from ready files; their translations
are AI-made, for a native speaker to read before launch, and their privacy
policies are drafts for the business's lawyer. It is made for the US first;
[SETUP.md](SETUP.md#another-country) lists what to check for another country
and what it does not support, such as languages written right to left.

</details>

> **Setting this up from the URL?** Once the repository is open locally, Codex
> should read [setup-client](.agents/skills/setup-client/SKILL.md). Both
> assistants follow [SETUP.md](SETUP.md).

## Limitations

<details>
<summary>Known limits of this version</summary>

- Notifications are Web Push only, with no email or SMS fallback. Battery
  savers on some Android phones can delay them, and an Android phone needs
  Google's services (in mainland China, use an iPhone).
- An iPhone needs iOS 16.4 or later and the dashboard added to its home
  screen.
- One owner login per business: no separate accounts for a team.
- One language per instance. Languages written right to left (Arabic, Hebrew,
  Persian, Urdu) are not supported, and on the business card, scripts whose
  letters join or change shape (Arabic, Hebrew, Hindi, Thai) are refused.
- Next to Call, a lead's second button opens a text, an email, WhatsApp or
  Telegram, whichever the seller chose; another messenger can only be the
  seller's stated preference.
- On Railway the database is backed up continuously for about 4 weeks;
  photos are not backed up.
- Handing a project over to the client's Railway account needs a paid plan
  on both accounts, and the client confirms it by email within 24 hours.

</details>

## More

- **Stack:** Python (FastAPI, SQLAlchemy, Alembic), Svelte 5 + TypeScript,
  PostgreSQL, S3-compatible storage, Web Push PWA. Deploys to Railway, or with
  Docker to a server of your own.
- **For developers:** the [technical docs](docs/README.md) and
  [CLAUDE.md](CLAUDE.md), the notes for changing the code.
- [Security](SECURITY.md): how to report a vulnerability privately

## Follow the series

⭐ Star the repo to follow the series, and follow [@ilyaxxing](https://instagram.com/ilyaxxing) on
Instagram for the next businesses.

## License

[MIT](LICENSE). The demo data is fictional and the car photos are
AI-generated. The launch video's music is made from GarageBand's Apple Loops
and is not under the MIT license.
