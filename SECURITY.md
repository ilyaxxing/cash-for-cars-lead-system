# Security

This system stores car sellers' personal data: names, phone numbers, email
addresses and photos of their cars, which can show plates, faces and homes. A
weakness in it can expose people who only wanted to sell a car, so please
report one privately.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting: the repository's **Security**
tab, then **Report a vulnerability**
(<https://github.com/ilyaxxing/cash-for-cars-lead-system/security/advisories/new>).
Please do not open a public issue, and do not test against a business's live
instance or with real people's data: run an instance of your own
([docs/development.md](docs/development.md)).

Include what an attacker could do, the steps to reproduce it on a local
instance, and the release tag or commit you tested. The report stays private
until a fix is released, and you are credited in the advisory if you wish.

## Supported versions

Fixes go into a new release. Every business runs its own instance, and the
person who installed it updates it to that release
([docs/deploy.md](docs/deploy.md#updating)).

## Scope

In scope: the app (`app/`, `frontend/`), the deploy scripts (`tools/deploy.py`,
`tools/deploy_vps.py`, `deploy/vps/`) and the project page with its demo
(`docs/`). Out of scope: Railway, GitHub and the push services themselves, and
an instance not set up as [SETUP.md](SETUP.md) says, for example one with a
weak `OWNER_PASSWORD`.
