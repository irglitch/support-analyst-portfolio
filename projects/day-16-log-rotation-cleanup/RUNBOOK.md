# Runbook — Log Rotation & Cleanup (Day 16)

## 1. Verify before you apply (5 minutes)
- Re-run the tool live on the affected host — a captured inventory is
  evidence, the live run is the current truth. Has anything been
  written since the inventory was captured, and is the batch that
  writes to `/var/log` running right now?
- Confirm the biggest file yourself before compressing it:
  `ls -lh /var/log/payment-api/app.log` and `du -sh /var/log/payment-api`
  — the report should match what the disk says.
- Spot-check the compression estimate on one file first: copy
  `app.log` to /tmp, `gzip` it, and compare sizes. Text logs usually
  shrink to ~10–15% of their size; if this one doesn't, the estimate
  in the report is optimistic and the real saving will be smaller.
- Confirm what is actually growing: `ls -lt /var/log/payment-api | head`
  — is the newest file the active one the tool skipped, or is something
  else writing now?
- Check whether any file in the DELETE list is needed for audit or an
  open incident: 120-day-old archives are usually safe, but if an
  incident from that period is still open, keep them and say so.

## 2. Escalate with facts, not feelings
Attach the report to the incident ticket and quote the action lines:
- **What:** `/var/log/payment-api` holds 28.00 GB across 6 files —
  the same directory the Day 14 disk check flagged at 28G
- **Recoverable:** 4 logs to compress (24.20 GB → ~20.57 GB freed)
  and 2 archives to delete (4.80 GB freed) — 25.37 GB in total,
  taking `/var/log` from 36.57 GB to ~11.20 GB
- **What is NOT touched:** `crm-sync/sync.log` is active (modified 15
  minutes ago) and is skipped; `README.txt` is not a log file
- **Risk if not done:** the directory grows back toward the Day 14
  disk-full incident — the settlement batch stops writing when the
  disk fills

Escalation path: Infrastructure / Linux admin team owns the rotation
policy and the scheduled job; application team copied — the app is a
victim of unrotated logs until proven otherwise. **Do not delete
anything yourself** unless the retention policy explicitly allows it:
old logs may be needed for audit or RCA.

## 3. Communicate
- Tell users and the duty manager what is happening in plain language:
  "the log disk is filling up with old, unrotated logs — we're
  compressing the old ones and deleting archives over 90 days old, and
  the logs the app is writing to right now are untouched."
- Say the run is a dry-run first and an apply second — nobody should
  be surprised by files disappearing.
- Update the ticket when the apply run finishes, with the measured
  space freed from the report (not the estimate).

## 4. After recovery
- Re-run the tool — it should report nothing to do (exit 0). Note the
  recovery timestamp and the measured space freed.
- Confirm the settlement batch that writes to `/var/log` completed
  cleanly after the cleanup — a batch that failed mid-write while the
  disk was full may need a re-run check (see Day 12).
- Schedule the tool: dry-run daily (alert on exit 1), apply weekly.
  A directory that filled up once will fill up again without a
  scheduled job — the point of this project is that the next one never
  becomes an incident.
- Re-check the disk a week later (see Day 14): if `/var/log` is
  growing again, the rotation job isn't running or the retention
  window is too long.

## 5. RCA prompts
- Why were there no rotation rules — was logrotate never configured
  for `payment-api`, or did its config break?
- Why did nobody notice until the disk check — add the Day 14 disk
  alert at 80% and this tool's dry-run as a daily scheduled check.
- Is 30/90 days the right retention — does audit need 90 days of
  plain logs, or is 30 days of plain + 90 days of compressed enough?
- Why is `payment-api` the fastest-growing log — is it logging at
  DEBUG level in production, or writing the same error in a loop?
- Problem record: if the directory fills every few weeks, this is a
  problem to fix (rotation policy, log level, bigger disk), not an
  incident to repeat.
