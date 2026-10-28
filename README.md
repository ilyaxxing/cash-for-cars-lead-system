https://github.com/user-attachments/assets/2933eead-924c-4a1b-bd94-473aa44d9013

# Cash for Cars Lead System

**Turn QR codes into car-buying leads.**

Business #1 of **100 Ready-to-Launch Businesses**: open source, free to copy,
yours to sell. By [@ilyaxxing](https://instagram.com/ilyaxxing).

[Live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/#how) ·
[Business model](docs/business.md) · [Setup guide](SETUP.md) ·
[Project page](https://ilyaxxing.github.io/cash-for-cars-lead-system/)

A lead system for businesses that buy used cars for cash. A seller scans the
QR code on a card left under their windshield wiper and fills in a two-minute
form on their phone; the buyer gets a push notification with the car, the
price and photos. Open source, for people who set it up for local car buyers:
each business gets its own copy, under its name and on its own accounts, set
up with Claude Code, and you charge for the setup.

## How it works

1. **QR cards.** The business leaves cards with a QR code under windshield
   wipers and puts the code on signs. The card comes as a print-ready file in
   their color, with their logo.
2. **The seller's form.** Car, condition, price, photos, contact. About two
   minutes, no app, no account.
3. **A push to the buyer** on their iPhone or Android, within seconds.
4. **The app.** Leads by status, photos, one tap to call, and statistics on
   which cards and places bring cars.

## The business

You install it for car buyers under their own name and charge for the setup.

**Who buys it:** cash-for-cars buyers, junk and salvage car buyers, small used
car lots and independent dealers. The best client already hands out cards or
puts up signs. **Where to find them:** "We buy cars" cards under wipers and
road signs, Google Maps, Facebook Marketplace and local groups, tow companies
and repair shops.

| | Price | What's included |
|---|---|---|
| Setup | $300-600 once | Turnkey: installation, their name, color and logo, their domain, the card PDF and QR codes, the app on the owner's phone |
| Support | $25-50 a month | Optional: changes, updates, someone to call |
| Hosting | about $5 a month (Railway Hobby, includes $5 of usage; not yet checked against a real client's bill) | On the client's own Railway account |
| Domain | about $10-15 a year | In the business's name, if it has none |

You pick the price, and whether to sell the setup alone or with monthly
support. Suggested starting points, not market-tested yet. More in
[docs/business.md](docs/business.md).

**Show it to a client.** Send the buyer [the page made for them](https://ilyaxxing.github.io/cash-for-cars-lead-system/for-buyers/):
the same live demo and what it does for their business, without prices,
setup details or GitHub. Add their name and color to the link
(`for-buyers/?name=Rapid+Cash+Cars&color=ff8a00`), or make it with the link
maker on the [project page](https://ilyaxxing.github.io/cash-for-cars-lead-system/#show).

## Get started

Open [Claude Code](https://claude.com/product/claude-code) (for example the
Code tab in the Claude desktop app) in an empty folder and send:

```text
Set up https://github.com/ilyaxxing/cash-for-cars-lead-system for my client.
```

Claude asks about the business, deploys it, connects the owner's phone and
makes the card and the QR codes. It tells you when a step needs a person:
signing in, payment, the domain's DNS settings. About an hour once the
accounts and the domain are ready.

- **You bring** Claude Code, which needs a paid Claude plan (Pro or higher)
  or an Anthropic API account, and your own [Railway](https://railway.com)
  account on the Hobby plan, $5 a month: each project is built there before
  it is handed over. These two are your own running costs.
- **The business brings** its own Railway account with its card, hosting
  about $5 a month (Railway Hobby, includes $5 of usage; not yet checked
  against a real client's bill); the finished project is handed over to it.
  Also its domain, its name and email, and the owner's phone for ten minutes.

Outside the US, Claude adapts the setup to the business's country: the
sellers' language, the questions, the privacy policy, the card's size, and a
server in that country where the law asks for one. It is tested end to end
for the US; [SETUP.md](SETUP.md#another-country) lists what to check for
another country and what does not work yet, such as languages written right
to left.

> **AI assistants:** follow [SETUP.md](SETUP.md).

## More

- **Stack:** Python (FastAPI, SQLAlchemy, Alembic), Svelte 5 + TypeScript,
  PostgreSQL, S3-compatible storage, Web Push PWA. Deploys to Railway, or with
  Docker to a server of your own.
- [The business in detail](docs/business.md)
- [Technical docs](docs/README.md), [SETUP.md](SETUP.md), [CLAUDE.md](CLAUDE.md)
- [Project page](https://ilyaxxing.github.io/cash-for-cars-lead-system/), with the
  [live demo](https://ilyaxxing.github.io/cash-for-cars-lead-system/#how)

## Follow the series

⭐ Star the repo to follow the series, and follow [@ilyaxxing](https://instagram.com/ilyaxxing) on
Instagram for the next businesses.

## License

[MIT](LICENSE). The demo data is fictional and the car photos are
AI-generated.
