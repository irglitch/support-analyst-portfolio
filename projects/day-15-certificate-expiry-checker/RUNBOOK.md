# Runbook — Certificate Expiry (Day 15)

## 1. Verify before you escalate (5 minutes)
- Re-run the checker with today's date (`--as-of` defaults to today) —
  is the expired certificate still expired, and has the critical one
  moved?
- Confirm the expired certificate with one independent check: try the
  service yourself (open the URL / attempt the SFTP connection) and note
  the exact error users see.
- Check whether the service is actually down or only at risk — an
  expired certificate on an internal tool is urgent; on the payment
  gateway it is a P1.

## 2. Escalate with facts, not feelings
Paste into the incident / renewal ticket:
- **Hostname + service + environment** — from the report table
- **Expiry date and days remaining** — negative means already expired
- **Owner team** — named in the report, so the ticket goes to the right queue
- **Impact if it lapses:** which users / partners / batches depend on it
  (e.g. the expired SFTP certificate blocks the overnight settlement file)

Escalation path: certificate owner first, platform/infrastructure team
copied. For the payment gateway, copy the duty manager — a Monday expiry
is a weekend job, not a Monday job.

## 3. Communicate
- Tell affected users/partners what is happening and the workaround, if
  any (e.g. settlement files held and re-sent after renewal).
- Never tell users to "click past the warning" or ignore a certificate
  error — that trains them to accept a real attack later.
- Update the ticket when the renewal is confirmed, not just when it is
  requested.

## 4. After recovery
- Re-run the checker — the renewed certificate should show a fresh
  expiry date and a green status; note the renewal timestamp.
- Verify the service end-to-end (one real transaction / one file
  transfer), not just the certificate date.
- Check knock-on effects separately: files that failed while the
  certificate was expired need re-sending; they do not fix themselves.

## 5. RCA prompts
- Why was this certificate not on the renewal calendar? Add every new
  certificate to the inventory the day it is issued.
- Why did monitoring not alert at 30 days? Schedule this checker weekly
  and alert on exit code 1 or 2.
- Who owns renewal for each service? If the inventory has no owner, the
  certificate has no owner — fix the inventory, not just the certificate.
- Problem record: link repeat expiries — one missed renewal is an
  incident, two is a process gap.
