# Interview Talking Points — How to Use This Portfolio Honestly

**The one-line opener:** "Alongside my 10+ years of support experience, I build a small
production-support scenario every day — here's one that mirrors a ticket type I've
handled: stuck transactions caused by a database connection failure."

## For Day 01 — Log Triage Analyzer
- **Situation:** Users report a symptom ("stuck in Pending"). Support's job is to find
  the failing layer fast, under SLA pressure.
- **Action:** I wrote a small Python tool that groups log errors by service and error
  code, with first/last seen, and suggests a priority — turning a 45-minute manual
  search into a one-page report I can paste into the ticket.
- **Result (in the scenario):** The dominant error is a DB connection timeout starting
  *before* the first user call — so escalation goes to the DB/infra team with evidence,
  and the knock-on file issue is tracked separately instead of being mistaken for the cause.
- **What it shows:** Triage thinking, not just coding — symptom vs. cause, escalation
  with facts, communication cadence, and RCA follow-up (see the runbook).

## For Day 02 — Linux Health Check Script
- **Situation:** Users report a vague symptom ("the app is slow") with no error
  message. Support's first job is to turn "slow" into facts before escalating.
- **Action:** I wrote a Bash script that runs the standard first-response checks —
  CPU load per core, memory, swap, disk space, top processes, and key service
  status — and writes a one-page PASS / WARN / FAIL report with an exit code
  monitoring can use. It also replays against a captured snapshot, so the same
  checks work on saved output from a server you can't reach right now.
- **Result (in the scenario):** The slow server fails three checks — root disk 92%
  full, load 2.10 per core, and the payment-api service stopped — with memory at
  88% and the app process itself burning 87% CPU. The vague "slow" becomes a
  concrete escalation: clear the disk, find why the service stopped, then restart it.
- **What it shows:** First-response triage under pressure, Linux basics, and
  escalating with evidence instead of a guess (see the runbook).

## For Day 03 — SQL Reconciliation Break Finder
- **Situation:** Finance reports the daily totals don't match — billing says
  $3,540.23, the ledger says $3,476.00 — and month-end close is blocked until
  the gap is explained. Both extracts have 16 transactions, so counting rows
  doesn't help.
- **Action:** I loaded both extracts into SQLite and ran reconciliation queries
  — totals per system, billed-but-never-posted, posted-but-never-billed, and
  same-transaction-different-amount — storing money as integer cents so the
  totals are exact. The tool writes a one-page report naming every break.
- **Result (in the scenario):** Exactly 4 transactions explain the whole
  $64.23 gap — one missing posting ($145.00), one orphan posting ($89.50),
  and two amount mismatches including a transposed digit ($210.00 vs $201.00).
  13 of 16 transactions match exactly, so finance chases 4 rows instead of
  re-checking the whole day.
- **What it shows:** SQL JOINs and the LEFT JOIN anti-pattern, reconciliation
  thinking, exact money handling, and escalating with named transactions
  instead of just a gap figure (see the runbook).

## For Day 04 — File Transfer Monitor
- **Situation:** The daily settlement file is due by 07:00 — finance
  reconciles against it and the downstream batch can't start without it.
  At 07:30 it still hasn't arrived, and checking the morning's four files
  by hand (transfer log, folder listing, timestamps, sizes) takes 15–20
  minutes and can miss a zero-byte file that *looks* like it arrived.
- **Action:** I wrote a Python tool that checks an expected-files manifest
  against the morning's transfer log and the real drop folder, and writes a
  one-page status report — OK / LATE / MISSING / EMPTY / SMALL per file —
  with an overall status and an exit code (0/1/2) a scheduler can use.
  It also flags files in the log but not on disk, and files that arrived
  without being in the manifest.
- **Result (in the scenario):** 🔴 ALERT — of 4 expected files only 1 is
  OK. The critical settlement file is MISSING, the audit log arrived as a
  zero-byte file (a failed transfer), and the FX rates file is 47 minutes
  late. An unexpected promo-codes file also needs confirming with the
  sender. Finance and the batch owners get the facts at 07:30 instead of
  finding out at 09:00.
- **What it shows:** Batch/settlement-file support, SLA awareness,
  verifying on disk instead of trusting the log alone, and escalating
  with named files and business impact instead of "the file is missing"
  (see the runbook).

## For Day 05 — Incident SLA Tracker
- **Situation:** At the 09:20 morning SLA review, ten incidents are open
  and nobody has checked the clock. The duty manager asks which tickets
  are breaching and which are about to — answering by hand means opening
  every ticket, remembering each priority's SLA target, and doing the
  arithmetic ten times over.
- **Action:** I wrote a Python tool that reads the incident export (CSV),
  works out each open ticket's resolution deadline from its priority's SLA
  target (P1: 4h, P2: 8h, P3: 24h, P4: 48h), and writes a one-page report
  sorted by deadline — BREACHED, AT RISK (under 2 hours or under 25% of
  the target left), or ON TRACK — with exit codes (0/1/2) a scheduler can
  page on. Resolved tickets are excluded; unknown priorities are flagged
  for a manual check instead of crashing the run.
- **Result (in the scenario):** 🔴 BREACH at 09:20 — 3 tickets already
  breached (INC-1042 P1 checkout 500s, 50m over; INC-1050 P1 settlement
  file rejected, 5m over; INC-1047 P3 report export timeout, 20m over)
  and 2 at risk, the next breach INC-1043 (P2 CRM sync) in just 40
  minutes. Five tickets are on track and one is resolved and excluded, so
  the team chases 5 tickets instead of re-reading all 11.
- **What it shows:** SLA tracking and breach prevention, incident
  prioritisation, and escalating with a deadline and an owner instead of
  "some tickets might be late" (see the runbook).

## Rules I follow
- These are **portfolio practice scenarios with sample data** — I say that plainly.
- I never claim a tool, employer, or certification that isn't on my CV.
- The value is the *support process* around the code: verify, escalate, communicate, RCA.
