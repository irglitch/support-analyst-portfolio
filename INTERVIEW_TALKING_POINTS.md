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

## Rules I follow
- These are **portfolio practice scenarios with sample data** — I say that plainly.
- I never claim a tool, employer, or certification that isn't on my CV.
- The value is the *support process* around the code: verify, escalate, communicate, RCA.
