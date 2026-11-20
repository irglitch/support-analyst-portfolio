# Runbook — Disk Space Early-Warning (Day 14)

## 1. Verify before you escalate (5 minutes)
- Re-run the script live on the affected host — a snapshot is evidence,
  the live run is the current truth. Has `/var` grown since 07:40, or
  has the batch already finished writing?
- Confirm the forecast yourself: `df -h /var` now vs the report, and
  check the time — if the fill estimate was ~5.8 hours at 07:40, the
  deadline is ~13:30 today.
- Confirm what is actually growing: `du -sh /var/log/*` — is it
  `payment-api` logs, or something else that started overnight?
- Check whether the batch on that mount is still running: a batch that
  is about to finish writing may stop growing on its own.

## 2. Escalate with facts, not feelings
Attach the report to the incident ticket and quote the FAIL/WARN lines:
- **Disk:** `/data` at 96% (480G of 500G, 20G free) and inodes at 90% —
  both FAIL; `/var` at 88%, filling in ~5.8 hours at +2.06%/h
- **What's taking it:** `/data/archives/settlements-2025` is 120G;
  `/var/log/payment-api` is 28G and still growing — most likely logs
  with no rotation
- **Deadline:** `/var` hits 100% around 13:30 today if nothing is
  cleared; when it does, the settlement batch can't write and the
  payment service stalls

Escalation path: Infrastructure / Linux admin team to clear or extend
space; application team copied — the app is a victim of the full disk
until proven otherwise. **Do not delete anything yourself** unless the
runbook for that directory explicitly allows it: old settlement
archives and application logs may be needed for audit or RCA.

## 3. Communicate
- Tell users and the duty manager what is happening in plain language:
  "the server's archive disk is almost full and the log disk fills up
  around lunchtime — we're clearing space before the batch is affected."
- Update the ticket every 30 minutes while a FAIL is open, even if the
  update is "no change".
- Never promise a time you don't control ("back in 10 minutes") —
  promise the next update instead.

## 4. After recovery
- Re-run the script — every check should be PASS, and the exit code 0.
  Note the recovery timestamp and how much space was freed.
- Re-check the disk a day later: if it filled up once, it will fill up
  again without log rotation or a cleanup job (see Day 16).
- Confirm the settlement batch that writes to `/var` completed cleanly
  after the space was freed — a batch that failed mid-write may need a
  re-run check (see Day 12).

## 5. RCA prompts
- What filled `/var` — logs with no rotation? A stuck batch writing
  errors in a loop? A backup landing in the wrong place?
- Why did `/data` reach 96% — are old settlement archives ever moved
  off, or do they accumulate forever?
- Why did nobody notice until the morning check — add a disk-space
  alert at 80% and a growth-rate alert (this script's forecast) so the
  next one pages support hours earlier.
- Why are inodes at 90% on `/data` — many small files (millions of
  tiny archive files?) rather than a few large ones? That changes the
  fix: archiving and compressing beats deleting one big file.
- Problem record: if a mount fills every few weeks, this is a problem
  to fix (rotation, retention policy, bigger disk), not an incident to
  repeat.
