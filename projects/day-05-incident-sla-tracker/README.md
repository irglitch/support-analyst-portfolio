# Day 05 — Incident SLA Tracker

## 📟 The situation (real-world use case)

**Wednesday, 09:20 — the morning SLA review.** Ten incidents are open and
nobody has checked the clock. The duty manager's first question is always the
same: *"Is anything breaching, and what's about to?"* Answering it by hand
means opening every ticket, reading its created time, remembering which SLA
target goes with which priority, and doing the arithmetic — ten tickets, ten
chances to miss the one that breached five minutes ago.

## 🔧 The fix

`sla_tracker.py` reads an incident export (CSV) and produces a one-page
**Incident SLA Report**:

- **Resolution deadline per ticket** from its priority's SLA target
  (P1: 4h, P2: 8h, P3: 24h, P4: 48h)
- **🔴 BREACHED** — past deadline, with how long ago it breached
- **🟠 AT RISK** — under 2 hours left, or under 25% of the SLA target
  remaining — whichever gives the earlier warning
- **🟢 ON TRACK** — everything else, so you can see at a glance what
  doesn't need chasing
- All open tickets **sorted by deadline**, so the next breach is always
  at the top
- Resolved/Closed tickets are excluded from the breach math; tickets with
  an unknown priority are flagged for a manual check instead of crashing
- **Exit codes a scheduler can use:** 0 = all on track, 1 = at least one
  at risk, 2 = at least one breached

## ▶️ Run it

```bash
cd projects/day-05-incident-sla-tracker
python3 sla_tracker.py sample_data/incidents.csv --out output/sla_report.md
cat output/sla_report.md
```

Check the queue as of a different time:

```bash
python3 sla_tracker.py sample_data/incidents.csv --now 2026-11-11T10:30 --out output/sla_report.md
```

**Result on the sample data (checked at 09:20):** 🔴 BREACH — 3 tickets
already breached (INC-1042 P1 checkout 500s, 50m over; INC-1050 P1
settlement file rejected, 5m over; INC-1047 P3 report export timeout,
20m over), 2 at risk (INC-1043 P2 CRM sync, 40m left; INC-1044 P3 invoice
PDF, 2h 40m left), 5 on track, 1 resolved and excluded. The next breach
is INC-1043 at 10:00 — chase it now, not at the next review.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

SLA tracking & breach prevention · Incident prioritisation · CSV data
handling · Python scripting · Support documentation · Escalation with
evidence

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
