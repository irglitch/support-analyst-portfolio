# Day 01 — Log Triage Analyzer

## 📟 The situation (real-world use case)

**Monday, 08:12.** Users start calling: transactions in the payments application are stuck
in **"Pending"**. The duty manager asks support three questions — *which service is failing,
when did it start, and is this a P1?* The application log for the morning is thousands of
lines long. Reading it by eye takes ~45 minutes and the clock on the SLA is already running.

## 🔧 The fix

`log_triage.py` reads the log in seconds and produces a one-page **Incident Triage Report**:

- Counts by level (INFO / WARN / ERROR / FATAL)
- **Errors grouped by service** — so you investigate the failing service, not the symptom
- **Errors grouped by code**, with first-seen → last-seen — so you get the start time and duration
- A **suggested priority** (P1/P2/P3 candidate) based on the error pattern — a database
  connection failure repeating across services is a dependency outage, not a user error
- A plain-English triage conclusion you can paste straight into the incident ticket

## ▶️ Run it

```bash
cd projects/day-01-log-triage-analyzer
python3 log_triage.py sample_data/app.log --out output/incident_report.md
cat output/incident_report.md
```

**Result on the sample data:** 13 errors — `payment-api` is the most affected service,
`DB_CONN_TIMEOUT` is the dominant code (10×, 08:12 → 08:28), priority suggested
**P1 (candidate)**. The "stuck Pending" symptom traces back to a database connection
failure that started at 08:12 — *before* the first user call. The missing settlement
file (`FILE_NOT_FOUND`) is a knock-on effect, listed separately so it isn't mistaken
for the root cause.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Log analysis · Incident triage & prioritisation · Problem management (symptom vs. cause) ·
Python scripting · Support documentation · SLA awareness

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
