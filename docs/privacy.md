# Privacy and personal data

What the system stores, for how long, and what it never does.

The privacy policy at `/privacy` is generated from
[locales/privacy-policy.en.md](../locales/privacy-policy.en.md) and the operator
settings. It is a starting point, not legal advice: have the client's lawyer
review it before launch.

Retention runs once at startup and then daily, and logs one line per pass.
It erases the seller's name, phone, email (every `personal: true` field) and
the photos 90 days after a lead is closed (Purchased or Rejected). The period
counts from closing, so leads still being worked keep their contacts. What it
cannot reach, and the policy says so: database backups until they rotate out,
notifications already shown, and calls and chats on both sides. Leads that
are never closed are never erased, so close the ones you are done with.

A visitor's IP address is used in memory for the rate limits and is never
stored, as the policy says, so it is kept out of every log: the app logs its
own events with ids only, uvicorn's access log is off, and on a server of the
client's own (docs/deploy-vps.md) Caddy's log filter drops the address, and
Docker keeps a few megabytes of each container's log, not an unlimited history.
On a server of the client's own, the daily database dumps are kept 14 days
(`BACKUP_DAYS`): that is the rotation the policy mentions.
