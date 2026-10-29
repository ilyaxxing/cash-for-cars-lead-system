# Technical documentation

For people changing the code, and for Claude Code. Setting up an instance for
a business is a guided process in [SETUP.md](../SETUP.md); the project's rules
for working on the code are in [CLAUDE.md](../CLAUDE.md).

| Document | What is in it |
|---|---|
| [Deploy and run an instance](deploy.md) | The client's settings file, the deploy script, the owner's phone, updates, a custom domain, QR codes, the business card, backups. |
| [Deploy on a server of the client's own](deploy-vps.md) | Where Railway does not suit (data that must stay in the country, no way to pay): any Linux server, Docker, HTTPS, daily dumps. |
| [Configuration](configuration.md) | Every setting, and client branding: color, logo, icon, welcome photo. |
| [Customize the form](customize-the-form.md) | The preset and locale formats, contact methods, another country. |
| [Privacy](privacy.md) | What is stored, retention, logs, the privacy policy. |
| [Development](development.md) | Features in detail, the stack, local setup and the checks. |

This folder also holds the project page for GitHub Pages
([index.html](index.html), with `.nojekyll` so it is served as it is), the
media the README shows (`media/`) and the page's live demo (`demo/`).
`for-buyers/` only forwards old links to the buyer site below. To publish the
page on a public
repository: Settings → Pages → Deploy from a branch → `main`, folder `/docs`.
It appears at `https://<owner>.github.io/<repository>/`; the README links to
it, and the page's repository links are set in one place at the top of
`index.html` (`data-repo`).

The README opens with the launch video (`media/cash-for-cars-lead-system.mp4`,
silent, 18 s): the question, one line in Claude Code, then what the client
gets. GitHub plays a video inside a README only when it is uploaded through
the website, and an upload made in a private repository is visible only to
people with access to it. So a new public copy, or a new video, needs its own
upload: open a new issue in the repository, drag the file into the comment
box, copy the `https://github.com/user-attachments/assets/...` link GitHub
inserts, and close the issue without submitting it. That link goes on the
first line of README.md in an ordinary commit. Editing README.md on the
website instead commits under the account's own email address unless "Keep
my email addresses private" is on in GitHub's email settings.

The live demo is the real seller's form and owner dashboard, built from
`frontend/` with a stand-in for the server that runs in the visitor's browser
(`frontend/src/demo`): a lead sent from the form arrives in the dashboard
with a push banner, and nothing typed leaves the page. The pages come from
the app itself, with a fictional business. There is one demo per country in
`../countries/`: the US at `demo/`, which this page shows, and every other
country at `demo/<code>/`, each with that country's language, form, prices,
units and made-up leads from its `demo.yaml`. After a change to the form,
the dashboard or a country, rebuild it and commit `demo/` and `assets/card/`:

```bash
.venv/bin/python tools/make_demo.py
```

Its car photos are AI-generated, with the makers' badges painted out; the
sources are kept out of git in `design-reference/demo-photos/`. A named link
recolors the apps as an instance would (`frontend/src/demo/palette.ts`
follows `app/branding/colors.py`); the static pages import that from
`demo/brand.js`.

**The buyer site.** The page installers send a car buyer lives at
https://car-buyer-demo.github.io/, a site of its own (the `car-buyer-demo`
organization's GitHub Pages), so a buyer who shortens the address cannot
reach this project's page and its prices. It shows the same demo in that business's
name and color from the link (`?name=...&color=...`), with no prices, setup
details or links back here, in the buyer's language: the US page at the
root, every other country at `/<code>/` (`/de/?name=...`), as the link maker
on this page picks it. Its source is the template `buyer-site/index.html`,
filled in from each country's `demo.yaml`; to publish a change (or a rebuilt
demo), build it into a clone of the site's repository and push, with a
neutral commit message:

```bash
git clone https://github.com/car-buyer-demo/car-buyer-demo.github.io.git /tmp/buyer-site
.venv/bin/python tools/make_buyer_site.py /tmp/buyer-site
git -C /tmp/buyer-site add -A && git -C /tmp/buyer-site commit -m "Update the demo" && git -C /tmp/buyer-site push
```

The card images on the page come from the card generator
(`app/branding/card.py`, rendered at 288 dpi as WebP by `tools/make_demo.py`),
so they are exactly what a client's print file looks like, in six accent
colors, in each country's language and card size (`assets/card/<code>/`).
