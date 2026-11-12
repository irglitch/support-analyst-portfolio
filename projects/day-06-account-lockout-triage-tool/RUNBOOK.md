# Runbook — Account Lockout Triage (Day 06)

## 1. Verify before you escalate (5 minutes)
- Re-run the tool on a **fresh export** — an account unlocked ten
  minutes ago must not be escalated as locked.
- Read the evidence, not just the label: a "locked" user whose
  password also expired yesterday needs a reset after the unlock, or
  they will call back immediately.
- Confirm the caller is who they say they are **before** any unlock or
  reset — employee ID, manager name, or the verification method your
  team uses. Never unlock on a voice match alone.

## 2. Escalate with facts, not feelings
Paste into the ticket / identity-team channel:
- **User + cause + evidence** — e.g. "priya.k locked at 09:05 after 5
  failed logins, 3 from the Mobile mail app — stale saved password
  suspected; password itself valid until 2026-12-20"
- **What the user needs** — unlock, reset, MFA re-enrol, or nothing
- **What must happen after the fix** — clear the saved password on the
  device, or it locks again within minutes
- **What you did NOT do** — "did not re-enable chen.l — account is
  disabled, needs manager approval"

Escalation path: a **locked** account goes to the identity team with
the evidence attached; a **disabled** account goes to the identity
team **with manager approval** — never re-enable it yourself. An
**expired password** or **MFA failure** is a helpdesk fix — no
escalation needed unless the reset itself fails.

## 3. Communicate
- Tell the user the cause in plain language, not the error code:
  "Your phone's mail app is trying an old password — that's what
  locked you out" beats "account locked, error 0x8009030C".
- Tell them what to do after the fix — update the saved password on
  every device, not just the one in front of them.
- For the expiring-soon users, a one-line heads-up today prevents
  tomorrow's lockout call: "Your password expires in 3 days — change
  it now while you're logged in."

## 4. After recovery
- Re-run the tool — the user should move to RESOLVED (a successful
  login after the fix) and drop out of the action lists.
- If the same user locks out again within a week, check for a second
  device with the old password — a phone, a tablet, a saved browser
  credential — before assuming user error.
- Log the lockout cause in the ticket, not just "unlocked": the
  pattern (stale mobile password, expired password, MFA) is what the
  weekly report is for.

## 5. RCA prompts
- Why did priya.k's phone keep retrying an old password — is there a
  self-service way for users to see which device is locking them out?
- How many of this week's lockouts were expired passwords that nobody
  warned about — should the 7-day expiry warning go out earlier, or
  automatically?
- Are MFA failures clustering on one authenticator app or one phone
  model? One broken authenticator is a user problem; ten is a rollout
  problem.
- Problem record: repeat lockouts for the same user or the same device
  are a pattern, not a coincidence — link them.
