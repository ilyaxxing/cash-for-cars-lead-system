# Development

Running the app locally, the checks that must pass, and how it is built.

## What it does

- **Seller form.** Mobile-first, one question per screen, built from a preset
  file. The lead is saved and the buyer is notified as soon as the contact step
  is done, so a seller who stops at the photo step is not lost.
- **Owner dashboard.** Installable web app (PWA) with leads by status, full
  lead details and photos, notes, one-tap call and WhatsApp, and statistics by
  source and conversion.
- **Push notifications.** Web Push, including iPhone (iOS 16.4+ home screen
  apps). Notifications carry the car and the price, never the seller's name or
  phone number.
- **Data retention.** The seller's name, phone, email and the photos are
  erased 90 days after a lead is closed. The car and the outcome are kept for
  statistics.
- **Spam protection.** A honeypot field and per-address rate limits. Addresses
  are counted in memory and never stored.
- **One instance per client.** Each business gets its own deployment, database
  and photo bucket. Everything client-specific is configured through
  environment variables and the form preset.

## Stack

Python 3.12, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL, S3-compatible
object storage, Svelte 5 + Vite. Deployed on Railway, or on a server of the
client's own ([deploy-vps.md](deploy-vps.md)).

## Local setup

Requirements: macOS or Linux (on Windows, WSL), Python 3.12, Node.js 22+,
Docker (or a local PostgreSQL), and
[gitleaks](https://github.com/gitleaks/gitleaks#installing).

```bash
# Secret and personal data scan on every commit
git config core.hooksPath .githooks

# Backend
uv venv --python 3.12 --seed .venv   # or: python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env

# Database
docker compose -f docker-compose.dev.yml up -d
.venv/bin/alembic upgrade head

# Frontend
npm ci --prefix frontend
npm run build --prefix frontend

# Run
.venv/bin/uvicorn --factory app.main:create_app --reload
```

Open http://localhost:8000 for the seller form and http://localhost:8000/app
for the dashboard (sign in with `OWNER_PASSWORD` from `.env`, then choose a
password of your own, as the first sign-in asks). To see the
dashboard with data, fill the development database with fictional leads:

```bash
.venv/bin/python -m app.cli seed-demo
```

While working on the frontend, `npm run dev --prefix frontend` serves it with
hot reload on http://localhost:5173 and proxies API calls to the backend.

Push notifications need VAPID keys in `.env` (`python -m app.cli vapid-keys`)
and a browser that allows notifications for `localhost`, such as Chrome.

## Checks

```bash
tools/check.sh
```

Runs the linter, the test suite against a throwaway PostgreSQL, the frontend
type check and build, and the secret scan. Everything must pass before a push.

The project page's live demo (`docs/demo`) is built from the same frontend;
after changing the form or the dashboard, rebuild it with
`.venv/bin/python tools/make_demo.py` ([docs/README.md](README.md)).

## Releases

Installers deploy release tags, not `main` (SETUP.md, docs/deploy.md). A
release is a `vX.Y.Z` tag on `main` once CI is green, with a GitHub Release
that says in a few lines what changed for an installer: a new setting, a
step to take, anything that needs a fresh `pip install`. Every change reaches
`main` through a pull request after CI passes.
