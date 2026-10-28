# Client files

`tools/deploy.py` puts a client's own files here in the upload it sends to
the server, next to the code: the logo, icon and welcome photo
(`brand/logo.png` and so on), and for a market the shipped files don't cover,
the form, the texts and the privacy policy (`brand/preset.yaml`,
`brand/locale.json`, `brand/privacy-policy.md`). It points `BRAND_LOGO`,
`BRAND_ICON`, `BRAND_PHOTO`, `PRESET_FILE`, `LOCALE_FILE` and
`PRIVACY_POLICY_FILE` at them. The client's originals stay in `clients/<id>/`
on the installer's machine.

Nothing else belongs here: the folder exists in git only so the Dockerfile
can copy it, and its other contents are ignored.
