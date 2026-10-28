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
media the README shows (`media/`), the page's live demo (`demo/`) and the
page installers send to a car buyer (`for-buyers/`: the same demo in that
business's name and color from the link, `?name=...&color=...`, with no
prices or setup details). To publish the page on a public
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
the app itself, with the default brand and a fictional business. After a
change to the form or the dashboard, rebuild it and commit `demo/`:

```bash
.venv/bin/python tools/make_demo.py
```

Its car photos are AI-generated, with the makers' badges painted out; the
sources are kept out of git in `design-reference/demo-photos/`. A named link
recolors the apps as an instance would (`frontend/src/demo/palette.ts`
follows `app/branding/colors.py`); the static pages import that from
`demo/brand.js`.

The card images on the page come from the card generator
(`app/branding/card.py`, rendered at 288 dpi as WebP), so they are exactly
what a client's print file looks like, in six accent colors.
