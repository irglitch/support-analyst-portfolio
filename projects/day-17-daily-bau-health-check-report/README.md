# Day 17 — Daily BAU Health-Check Report

## 📟 The situation (real-world use case)

**Monday, 09:20.** The business day is about to start and the duty
manager asks the one question support dreads most: *"is everything OK
this morning?"* Until now the answer meant opening five different
places — the service probe log (Day 13), the disk report (Day 14),
the incident queue (Day 05), the file-transfer manifest (Day 04) and
the certificate inventory (Day 15) — and stitching the picture
together by hand while the 10:00 batch and the SLA clock both run.
Anything missed in that scramble becomes the morning's incident.

## 🔧 The fix

`bau_report.py` reads one snapshot of each of the five areas (CSV —
produced by the checks from the earlier days, or by the live collector
in `run_bau_check.sh`) and writes a single one-page **BAU report**:

- An **overall verdict** — 🟢 GREEN / 🟡 AMBER / 🔴 RED — with an exit
  code (0/1/2) a scheduler can page on
- A **status per area** (services, disk space, incident SLA, files,
  certificates) with the headline counts
- A **ranked action list** — worst first, then by deadline — so the
  team works the item that hurts the business first, not the one
  they happened to see first
- The detail tables underneath, so any action can be verified against
  the raw numbers before anyone escalates

`run_bau_check.sh` is the daily entry point: on its own it reports
from the snapshot; with `--live` it first collects a live snapshot on
a Linux host (`df` for disks, `systemctl`/`pgrep` for services) and
then reports on that. Values a live check cannot measure (latency,
uptime, growth) are shown as "—", never invented.

## ▶️ Run it

```bash
cd projects/day-17-daily-bau-health-check-report
AS_OF=2026-11-23T09:20 ./run_bau_check.sh
cat output/bau_report.md
```

Or the tool directly:

```bash
python3 bau_report.py --input-dir sample_data --as-of 2026-11-23T09:20 --out output/bau_report.md
```

Live snapshot on this host, then the report:

```bash
./run_bau_check.sh --live
```

**Result on the sample data:** 🔴 **RED** at 09:20 — all five areas
are CRITICAL at once, and the ranked list says why the morning is bad
before anyone has to read five tools:

1. **notification-service DOWN** since 09:02 (3 failed probes,
   "Connection refused") — page the platform team first
2. **settlement-20261123.csv MISSING** (due 07:00) — the downstream
   batch cannot start until the partner bank re-sends it
3. **Payment Gateway API certificate expires TODAY** — renew before
   payments break (flagged as "expires Monday" back on Day 15)
4. **INC-2011 (P1, checkout 500s) BREACHED** — 35 minutes over SLA
5. **/data at 91%** — fills around 15:45 at +1.4%/h if nothing is cleared

Below the criticals: settlement-service DEGRADED at 1180 ms against
an 800 ms threshold, INC-2014 (P2) breaches in 30 minutes, the FX
rates file arrived 25 minutes late, and the SSO (19 days) and Customer
Portal (24 days) certificates need renewal tickets. The good news is
real too: crm-sync is back UP after Sunday evening's outage, payment-api
is healthy, and 3 of the 5 open tickets are on track — the report
shows the clean areas alongside the bad ones, so the team knows what
*doesn't* need chasing.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
bash tests/test_run_bau_check.sh
```

## 🛠 Skills demonstrated

Morning BAU / health-check reporting · Combining several monitoring
sources into one verdict · Incident triage & prioritisation · SLA
awareness · Disk capacity forecasting · Certificate lifecycle
awareness · File-transfer monitoring · Python scripting · Bash / Linux
basics (`df`, `systemctl`, `pgrep`) · Scheduler-friendly exit codes

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
