# Runbook — File Transfer Monitor (Day 04)

## 1. Verify before you escalate (5 minutes)
- Re-check the drop folder directly — is the file really absent, or did the
  transfer log just miss it? The tool's `--drop-dir` check already does this,
  but confirm by eye before paging anyone.
- Check the transfer system's own status page / SFTP logs: did the sender
  connect at all, or did the connection fail mid-transfer? A zero-byte file
  usually means the sender's job failed or the transfer was interrupted.
- Check whether the file arrived under a *different name* (date format,
  `_v2`, `.tmp` suffix) — a rename is the most common "missing file" that
  isn't actually missing.

## 2. Escalate with facts, not feelings
Paste into the incident ticket:
- **Which file:** name, expected-by time, source system
- **What the check found:** MISSING / EMPTY / LATE, with the received time
  and size (or the lack of them)
- **Business impact:** from the manifest — what is blocked (here: finance
  reconciliation + downstream batch)
- **What is fine:** name the files that *did* arrive, so nobody re-sends
  the whole morning

Escalation path for a missing settlement file: the **sending party**
(payment processor / partner) first, with the operations / batch team copied
— the file is produced outside your system, so the fix starts with them.
For an EMPTY file, ask the sender to re-send; never "fix" a zero-byte file
by hand-editing it.

## 3. Communicate
- Tell finance and the batch owners the moment the check fails — at 07:30,
  not when they notice at 09:00. Give them the expected re-send time once
  the sender confirms it.
- Update the ticket when the file lands: received time, size, and whether
  the downstream batch was re-run.
- Do **not** start the downstream batch on a partial or empty file "to save
  time" — a batch that runs on bad input creates a second incident.

## 4. After recovery
- Re-run the monitor — status should be all OK; note the recovery time.
- Confirm the downstream batch ran and finance reconciled; check the totals
  tie out (see Day 03 — a re-sent file can still have a data gap).
- Add the unexpected file to the manifest if it turns out to be a legitimate
  new feed; if it was misdirected, tell the sender.

## 5. RCA prompts
- Why did the sender's job fail — and why did nobody on their side notice
  before 07:00?
- Should this check run automatically at 07:05 instead of manually at 07:30?
  (Exit codes 0/1/2 are built for exactly that.)
- Was the zero-byte file a one-off, or does the audit-log job fail
  regularly? One failure is an incident, a pattern is a problem.
