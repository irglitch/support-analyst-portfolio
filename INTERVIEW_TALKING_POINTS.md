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

## Rules I follow
- These are **portfolio practice scenarios with sample data** — I say that plainly.
- I never claim a tool, employer, or certification that isn't on my CV.
- The value is the *support process* around the code: verify, escalate, communicate, RCA.
