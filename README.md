# Application Support Analyst — Real-World Scenario Portfolio

**Puneeth Kumar Halthur Bhaskar** · Support Engineer / Application Support Analyst · Toronto, ON, Canada
📧 puneethcvpro8@gmail.com · 💼 Open to Application Support / Production Support / Operations Support roles — Toronto/GTA & remote Canada

> A growing portfolio of **simple, real-world production support fixes** — one project a day.
> Every project starts from a situation a support analyst actually gets paged for, then shows the
> triage, the fix, and the runbook. These are **practice scenarios built for this portfolio**,
> using sample data — they are not work taken from any employer.

---

## What this portfolio proves

| Support skill (from live job postings) | Where it's demonstrated |
|---|---|
| Incident triage & prioritisation (P1/P2) | Day 01 — Log Triage Analyzer |
| Log analysis & problem management | Day 01, Day 07, Day 23 |
| Linux / system health checks | Day 02, Day 14, Day 17 |
| SQL — reconciliation, data validation | Day 03, Day 08–Day 11 |
| File transfer monitoring (batch / settlement files) | Day 04, Day 12 |
| SLA tracking & breach prevention | Day 05, Day 22 |
| Monitoring & alerting automation | Day 13–Day 17 |
| Change / release support | Day 19, Day 20 |
| Root Cause Analysis (RCA) documentation | Day 18, every project's runbook |

**Tools used across the portfolio:** Python · SQL (SQLite) · Bash / Linux basics · Git & GitHub ·
CSV/JSON data handling · Markdown runbooks

**Background:** 10+ years in application / software support (telecom provisioning, CRM & billing,
banking risk-analytics support) — incident handling, user support, data validation, UAT/defect
support, and documentation. Full history is on my CV / LinkedIn; this repo shows the *hands-on* side.

---

## Projects

| Day | Project | Scenario in one line | Status |
|---|---|---|---|
| 01 | [Log Triage Analyzer](projects/day-01-log-triage-analyzer/) | Transactions stuck "Pending" — find the failing service in a 4,000-line log in minutes, not 45 | ✅ Done 2026-11-07 |
| 02 | [Linux Health Check Script](projects/day-02-linux-health-check/) | "The app is slow" — root disk 92% full, service down, one process at 87% CPU | ✅ Done 2026-11-08 |
| 03 | [SQL Reconciliation Break Finder](projects/day-03-sql-reconciliation-break-finder/) | Finance totals don't match — 4 named transactions explain a $64.23 gap, 13 of 16 match exactly | ✅ Done 2026-11-09 |
| 04 | [File Transfer Monitor](projects/day-04-file-transfer-monitor/) | The 7 AM settlement file never arrived — detect it before the business does | ✅ Done 2026-11-10 |
| 05 | [Incident SLA Tracker](projects/day-05-incident-sla-tracker/) | 09:20 SLA review: 3 tickets already breached, 2 more breach within hours — chase the right ones first | ✅ Done 2026-11-11 |
| 06 | [Account Lockout Triage Tool](projects/day-06-account-lockout-triage-tool/) | Locked-out user: priya.k locked by a stale phone password, sam.r expired, ana.m's MFA failing — check the causes in order | ✅ Done 2026-11-12 |
| 07 | Error Code Knowledge Base | Searchable past-incident fixes | ⏳ Scheduled |

Full 30-day plan: **[ROADMAP.md](ROADMAP.md)**

---

## How each project is structured

```
projects/day-XX-<name>/
├── README.md        # The situation, the problem, the fix, how to run it
├── <tool>.py/.sh/.sql   # The actual working fix — no external dependencies where possible
├── sample_data/     # Realistic sample data you can run it on right away
├── output/          # A real generated report from running the tool
└── RUNBOOK.md       # What a support analyst does with the result: triage, escalate, RCA
```

## How to run any project

Each project README has copy-paste commands. Day 01, for example:

```bash
cd projects/day-01-log-triage-analyzer
python3 log_triage.py sample_data/app.log --out output/incident_report.md
```

## Honesty note

Sample scenarios, sample data, real code. Nothing here claims experience with a tool or employer
that isn't on my CV — in interviews I talk about these as portfolio practice that mirrors the
day-to-day work of application support, alongside my actual support experience.

## License

MIT — see [LICENSE](LICENSE).
