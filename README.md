https://github.com/user-attachments/assets/1d80405d-8d4f-474a-80df-4143831ba948

**[Try the live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/) · [Start with SETUP.md](SETUP.md)**

# Cash for Cars Lead System

**Set up a branded lead system for local car buyers, and charge for the setup.**

Business #1 of **100 Ready-to-Launch Businesses**: open source, free to copy,
yours to sell. By [@ilyaxxing](https://instagram.com/ilyaxxing).

Give a car buyer QR codes and links for their cards, signs and online
listings. Sellers send their car through a short form, and the buyer gets a
push on their phone in seconds, with every lead in one app.

Suggested price: $300–600 per setup, plus optional monthly support (starting
estimates, not yet tested with clients). The business pays its own hosting and
domain.

[Try the live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/) ·
[Set it up with Claude Code](#get-started) · [Business model](docs/business.md)

## How it works

1. **QR codes and links.** A seller scans a code or opens a link wherever
   they see it: a card under a wiper (it comes as a print-ready file in the
   buyer's color, with their logo), a sticker on the buyer's own car, a
   poster at a partner repair shop, a sign or banner, a link in the Google
   Maps listing, and more ([every place](docs/business.md#where-leads-come-from)).
   Each place gets its own code or link, so statistics tell them apart.
2. **The seller's form.** Car, condition, price, photos, contact. A few
   minutes, no app, no account.
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
| Support | $25-50 a month | Optional: changes, updates, someone to call |
| Hosting | about $5 a month | On the client's own Railway account |
| Domain | about $10-15 a year | In the business's name, if it has none |

Hosting, the domain and printing are paid by the client directly, on top of the setup price.

Hosting is Railway's Hobby plan, $5 a month with $5 of usage included. In practice
instances like this fit within Hobby's included usage; check the first client's bill.

You pick the price, and whether to sell the setup alone or with monthly
support. Suggested starting points, not market-tested yet. More in
[docs/business.md](docs/business.md).

**Show it to a client.** [The page for car buyers](https://car-buyer-demo.github.io/)
has the same live demo and what it does for their business, without prices,
setup details or GitHub. Send it in their name and color: add them to the link
(`https://car-buyer-demo.github.io/?name=Rapid+Cash+Cars&color=ff8a00`), or make it with the link
maker on the [project page](https://ilyaxxing.github.io/cash-for-cars-lead-system/#show), which
also picks the buyer's country and language: eleven of them, as in [countries/](countries/).

## Get started

Open [Claude Code](https://claude.com/product/claude-code) (for example the
Code tab in the Claude desktop app) in an empty folder on a Mac or a Linux
computer (on Windows, inside WSL) and send:

```text
Set up https://github.com/ilyaxxing/cash-for-cars-lead-system for my client.
```

Claude asks about the business, deploys it, connects the owner's phone and
makes the card and the QR codes. It tells you when a step needs a person:
signing in, payment, the domain's DNS settings. About an hour for the setup
itself once the accounts are ready; handing the project over to the business
and the domain's DNS can take up to a day.

- **You bring** Claude Code, which needs a paid Claude plan (Pro or higher)
  or an Anthropic API account, and your own [Railway](https://railway.com)
  account on the Hobby plan, $5 a month: each project is built there before
  it is handed over. These two are your own running costs.
- **The business brings** its own Railway account with its card, hosting
  about $5 a month; the finished project is handed over to it.
  Also its domain, its name and email, and the owner's phone for ten minutes.

<details>
<summary><b>Other countries</b></summary>

The system can be adapted for other countries: Claude changes the sellers'
language, the questions, the privacy policy, the card's size and, where
needed, where it runs. The legal side needs a local check: where sellers'
data may be kept, whether it may leave the country and what the business
must register are for its local lawyer to confirm. For the countries in
[countries/](countries/) it starts from ready files; their translations
have not been reviewed by native speakers yet, and their privacy policies
are drafts for the business's lawyer. It is tested end to end for the US;
[SETUP.md](SETUP.md#another-country) lists what to check for another country
and what does not work yet, such as languages written right to left.

</details>

> **AI assistants:** follow [SETUP.md](SETUP.md).

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
  Persian, Urdu) are not supported yet, and on the business card, scripts
  whose letters join (Arabic, Hindi, Thai) are refused.
- Next to Call, a lead's second button opens a text, an email, WhatsApp or
  Telegram, whichever the seller chose; another messenger can only be the
  seller's stated preference.
- Restoring the database from a backup has not been rehearsed yet. On Railway,
  photos are not backed up.
- Handing a Railway project over to the client's own account follows
  Railway's documentation and has not been done with a real client yet. A
  server of the client's own has been tested on a local virtual machine, not
  yet with a public domain and a real certificate.
- Prices are suggestions, not tested on real clients yet.

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
