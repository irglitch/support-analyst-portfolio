# Day 14 — Disk Space Early-Warning Script

## 💾 The situation (real-world use case)

**Friday, 07:40.** The overnight settlement batch writes its files to
`/var`, and the morning check shows it at **88% — up from 64% at 8 PM
last night**. The archives mount `/data` is sitting at **96%**. If
`/var` hits 100%, the batch can't write, the application can't log,
and the payment service stalls — and at the current growth rate that
happens before lunch. The duty manager asks the one question that
matters: *which mounts are at risk, how long do we have, and what's
taking the space?* A plain `df` answers only the first part.

## 🔧 The fix

`disk_watch.sh` (Bash, standard tools only) checks every filesystem
and produces a one-page **Disk Space Early-Warning Report**:

- **Usage vs thresholds** — WARN at 80%, FAIL at 90% per mount
- **Growth forecast** — from an hourly usage history it works out the
  growth rate (%/h) and the estimated hours until full. A mount at 70%
  growing 5%/h is more urgent than one at 88% that has been flat for a
  week — the forecast is what makes this an *early-warning* tool, not
  just a `df` wrapper
- **Inode usage** — a filesystem can be "full" on inodes while `df`
  still shows free space, so inodes get their own check at the same
  thresholds
- **Largest directories** — on any mount over its warning threshold,
  the biggest directories are listed and anything ≥ 10G is flagged to
  investigate first, so the first action is obvious

The tool only reads and reports — it never deletes anything. Clearing
space is a human decision; support supplies the evidence.

## ▶️ Run it

```bash
cd projects/day-14-disk-space-early-warning
bash disk_watch.sh --snapshot sample_data/filling_up --out output/disk_watch_report.md
cat output/disk_watch_report.md
```

Exit codes: `0` = all filesystems healthy, `1` = at least one WARN,
`2` = at least one FAIL (or a usage error) — so a scheduler can alert
on a non-zero exit.

Live mode (checks this host; pass `--history` with an hourly
`timestamp,mount,used_pct` CSV to get growth forecasts, otherwise
growth shows as "no usage history"):

```bash
bash disk_watch.sh --out output/disk_watch_live.md
```

**Result on the sample data:** 🔴 **FAIL — a filesystem needs action
now.** `/data` is at **96%** (480G of 500G, 20G free) and its inodes
are at **90%** — both FAIL. `/var` is at **88%** (176G of 200G, 24G
free) and growing at **+2.06%/h**, so it **fills in ~5.8 hours** —
around 13:30 today if nothing is cleared. The largest directory is
`/data/archives/settlements-2025` (120G), and the fastest-growing one
is `/var/log/payment-api` (28G) — most likely logs with no rotation,
which is a Day 16 problem to fix permanently.

The healthy snapshot (`sample_data/healthy`) passes clean: exit 0,
`/var` at 58% growing at only +0.26%/h — ~163 hours to full, no action
needed. Its report is at `output/disk_watch_report_healthy.md`.

Run the tests:

```bash
bash tests/test_disk_watch.sh
```

## 🛠 Skills demonstrated

Linux disk monitoring (`df`, `du`, inodes) · Capacity planning &
growth forecasting · Threshold-based alerting · Incident prevention
(acting before the outage, not after) · Bash scripting · Support
documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
