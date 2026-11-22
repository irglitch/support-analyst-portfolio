# Day 16 — Log Rotation & Cleanup Automation

## 🗂️ The situation (real-world use case)

**Sunday, 09:20.** Two days ago the disk check (Day 14) flagged
`/var/log/payment-api` at **28G** — the fastest-growing directory on
the server, and the note next to it said "most likely logs with no
rotation". That was the diagnosis; this is the fix. The duty manager
doesn't want another manual delete before every batch window — she
wants rotation and cleanup **automated, with a retention policy, and
safe enough to schedule**: old logs get compressed, ancient archives
get deleted, the log the application is writing to right now is never
touched, and nothing is ever deleted without a dry-run first. A
cleanup script that deletes the wrong file is worse than a full disk —
it destroys the evidence an incident investigation needs.

## 🔧 The fix

`log_rotate.sh` (Bash, standard tools only) scans a log directory —
or a captured inventory of one — and applies a retention policy:

- **COMPRESS** — plain `.log` files older than 30 days get gzipped
  (default `--retention-days 30`)
- **DELETE** — `.log.gz` archives older than 90 days get deleted
  (default `--delete-days 90`)
- **KEEP** — anything inside its retention window is left alone
- **SKIP (active)** — a file modified in the last 60 minutes is still
  being written to, so it is never rotated, even if you pass
  `--retention-days 0`
- **SKIP (not a log)** — anything that isn't a `.log` file is listed
  and left alone; the tool only ever acts on log files

Safety is the point, not a side effect:

- **Dry-run by default.** Without `--apply` nothing is compressed or
  deleted — the report shows exactly what *would* happen. A scheduler
  can run the dry-run daily and alert on exit 1 (cleanup pending).
- **Manifest mode is report-only.** `--apply` with a captured
  inventory is refused outright — the files listed may not exist here.
- **`--dir /` is refused**, and a missing directory is an error.
- **`--apply` reports measured space freed**, not the estimate: each
  compressed file's real saving is measured after `gzip` runs.

## ▶️ Run it

```bash
cd projects/day-16-log-rotation-cleanup
bash log_rotate.sh --manifest sample_data/inventory.txt --now '2026-11-22 09:20' --out output/log_rotation_report.md
cat output/log_rotation_report.md
```

Exit codes: `0` = all logs within policy (or `--apply` finished
cleanly), `1` = dry-run found files to compress/delete (cleanup
pending), `2` = usage/safety error or an `--apply` action failed — so
a scheduler can alert on a non-zero exit.

Live mode (scans a real directory; dry-run unless you pass `--apply`):

```bash
bash log_rotate.sh --dir sample_data/logs --out output/log_rotation_report_sample_tree.md
bash log_rotate.sh --dir /var/log --apply --out output/log_rotation_live.md   # only when you mean it
```

Capture an inventory from a production host and review it here first:

```bash
find /var/log -type f -printf '%s %T@ %p\n' > inventory.txt
bash log_rotate.sh --manifest inventory.txt --now '2026-11-22 09:20' --out output/log_rotation_report.md
```

**Result on the sample data:** 🟡 **DRY-RUN — cleanup pending (exit
1).** 14 files scanned, **36.57 GB** in total. **4 logs to compress**
(24.20 GB — `payment-api/app.log` 9.20 GB at 45 days,
`app.log.1` 6.40 GB at 52 days, `error.log` 5.00 GB at 38 days,
`settlement-batch/batch.log` 3.60 GB at 60 days), freeing an
estimated **20.57 GB**, and **2 archives to delete** (`app.log.2.gz`
3.60 GB at 120 days, `batch.log.1.gz` 1.20 GB at 110 days), freeing
**4.80 GB** — **25.37 GB recoverable in total**, taking `/var/log`
from 36.57 GB to ~11.20 GB. `/var/log/payment-api` alone is
**28.00 GB** across 6 files — the same directory Day 14 flagged.
The currently-written `crm-sync/sync.log` (modified 15 minutes ago)
is **skipped as active**, and `/var/log/README.txt` is **skipped as
not a log file**. Nothing was changed by this run.

The small live tree (`sample_data/logs`) shows the same behaviour on
real files: 8 files, 38.72 KB, 4 to compress and 1 archive to delete,
an estimated 27.21 KB freed, exit 1. Its report is at
`output/log_rotation_report_sample_tree.md`.

Run the tests:

```bash
bash tests/test_log_rotate.sh
```

## 🛠 Skills demonstrated

Linux log management (`find`, `gzip`, file ages) · Retention policy
design (compress vs delete windows) · Safe automation (dry-run by
default, active-file guard, report-only snapshots) · Capacity
recovery with measured vs estimated savings · Scheduler-friendly exit
codes · Bash scripting · Support documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
