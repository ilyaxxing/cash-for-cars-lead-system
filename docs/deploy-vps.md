# Deploy on a server of the client's own

For a client Railway does not suit: a country whose law keeps personal data
at home (in Russia, sellers' names and phones must be stored on servers in
Russia), a business that cannot pay Railway, or one that wants its own
server. The instance is the same app as on Railway; only where it runs
differs. [SETUP.md](../SETUP.md) drives these steps for an installer.

One command deploys and updates it, `tools/deploy_vps.py`, with the client's
settings file in and a working address out, as `tools/deploy.py` does for
Railway ([Deploy and run an instance](deploy.md)).

## Before you start

- **A server in the client's name**: Ubuntu 24.04, 2 GB of memory (the build
  needs it), 20 GB of disk and a public IPv4 address, at a provider in the
  client's country. Any provider works.
- **SSH access with a key.** The installer's public key
  (`~/.ssh/id_ed25519.pub`; `ssh-keygen -t ed25519` makes one) is added when
  the server is created, in the provider's panel, or once with
  `ssh-copy-id root@<address>` and the root password. The script signs in with
  the key only.
- **The client's domain, pointing at the server**: an A record such as
  `buy.example.ru` → `203.0.113.10` at the registrar, before the first
  deploy. Caddy gets the HTTPS certificate for it, which needs the record in
  place.
- This repository with the Python environment from
  [local setup](development.md#local-setup), and a clean git checkout of the
  commit to ship.

## Settings

The client's settings file is the same as for Railway (`.env.example`), plus:

```bash
VPS_HOST=root@203.0.113.10          # the server, over SSH
PUBLIC_URL=https://buy.example.ru   # required: the client's domain
DOCKER_MIRROR=                      # optional, see below
BACKUP_DAYS=14                      # optional: how long the daily dumps are kept
```

The script fills in `SECRET_KEY`, the VAPID keys and `POSTGRES_PASSWORD` the
first time and writes them back into the file; keep them, as on Railway.

Where Docker Hub is slow or closed, `DOCKER_MIRROR` names a mirror the server
pulls images through: the hosting provider's own, if it has one, or
`https://mirror.gcr.io`.

## Deploy

```bash
.venv/bin/python tools/deploy_vps.py clients/acme.env
```

It checks the code, the settings (as production loads them, with the
client's own files) and that the domain points at the server; installs
Docker if it is missing (Ubuntu's packages); uploads exactly the commit with
the client's own files and the settings (over SSH's stdin, never on a
command line) to `/opt/cash-for-cars/<name>/`; starts
[deploy/vps/compose.yaml](../deploy/vps/compose.yaml); and waits until
`https://<domain>/healthz` reports the commit and the latest migration. The
first run takes 5-15 minutes, most of it the build.

On the server:

- `app`: the same image as on Railway; migrations run before it answers.
- `db`: PostgreSQL 16 in a Docker volume.
- `backup`: a dump of the database every day, kept `BACKUP_DAYS` days, in
  the `backups` volume.
- `caddy`: HTTPS with a certificate it gets and renews, in front of the app.
  It passes the visitor's address in `X-Real-IP` from the connection itself
  (`CLIENT_IP_HEADER`), never from what a visitor sends.

Photos are kept in a volume (`STORAGE_BACKEND=volume`), as they would be in
Railway's bucket, and are not in the dumps: they are working material that
retention erases anyway.

## Updating

Pull the new code, run the checks, and run the same command again. Migrations
run before the new version starts serving.

## Logs, backups, restore

The script prints the command for the app's log at the end:

```bash
ssh root@203.0.113.10 'docker compose -p <name> logs app'
```

The dumps are on the server itself (`app-<date>.sql.gz` in the `backups`
volume). For a copy elsewhere, turn on the provider's server backups, or copy
a dump off the server now and then. To restore one, from
`/opt/cash-for-cars/<name>` on the server:

```bash
compose="docker compose -p <name> --project-directory . -f src/deploy/vps/compose.yaml"
$compose stop app
$compose exec -T db psql -U app -d app -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
$compose exec -T backup sh -c 'gunzip -c /backups/app-<date>.sql.gz' | $compose exec -T db psql -U app -d app
$compose start app
```

## Hand over

The client owns the server and the domain. The installer's key is the only
way in: with a support plan it stays; without one, the client removes it in
the provider's panel or from `/root/.ssh/authorized_keys`. The settings file
stays with whoever supports the system, as with Railway.
