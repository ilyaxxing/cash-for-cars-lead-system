---
name: setup-client
description: Install Cash for Cars Lead System for a client or a car-buying business. Use for a setup request with the repository URL or from an existing checkout, through deployment and handover.
---

Read [SETUP.md](../../../SETUP.md) and follow it in the person's language.
For a new installation, ask which country and language the sellers need
before step 1. To resume, use the same repository folder and release. Check
what is already configured without printing secrets, and ask for the next
missing detail or confirmation.

- Ask with the available Codex question tool when it supports the required
  input. Otherwise end the turn with one question in chat. Offer short,
  numbered choices and a write-in answer. Run the technical steps yourself.
- Use the same checkout for step 1 and client setup. Follow the release
  checks in SETUP.md before preparing files. If local changes prevent the
  switch, pause and preserve them.
- Claude's `!` shortcut is specific to Claude Code. For Railway, run the
  guide's browser login flow and verify the account after the person signs
  in. For SSH, have them enter any password in their own terminal. Keep
  credentials out of tool output and client settings and assets under the
  release's Git-ignored paths.
- Before creating infrastructure or incurring a charge, name the resources,
  account and expected cost and wait for explicit agreement. Confirming the
  settings alone does not authorize deployment. For a rehearsal, prepare
  locally and stop before provisioning or running either deploy script.
