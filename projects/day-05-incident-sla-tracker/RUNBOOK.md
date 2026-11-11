# Runbook — Incident SLA Tracking (Day 05)

## 1. Verify before you escalate (5 minutes)
- Re-run the tracker on a **fresh incident export** — the sample CSV is a
  snapshot; a ticket resolved five minutes ago must not be escalated.
- Open the top breached ticket and confirm its status — is it really still
  open, or is the fix deployed and the ticket just not closed yet?
- Check the at-risk tickets the same way: is the fix already in progress,
  or is the assignee blocked and waiting on someone?

## 2. Escalate with facts, not feelings
Paste into the incident ticket / duty-manager channel:
- **Ticket + priority + deadline** — e.g. "INC-1042 (P1), deadline 08:30,
  breached 50m ago"
- **Impact in one line** — the summary field, not the ticket number alone
- **What is being done** — assignee, current status, next step and ETA
- **Breach reason** — why it slipped (waiting on a vendor? fix failed
  testing? nobody picked it up?) — record it now, not at the weekly review

Escalation path: a **P1 breach** goes to the duty manager immediately; a
P2/P3 breach goes to the team lead with the duty manager copied. An at-risk
P1 gets chased with the assignee first — escalate only if there is no
credible plan to land the fix before the deadline.

## 3. Communicate
- Update every breached ticket the same morning — "breached at 08:30,
  fix in progress, ETA 11:00" beats silence, even when the news is bad.
- Tell the business contact for the affected service, not just the ticket
  queue — they are the ones answering user questions.
- For at-risk tickets, post the deadline in the ticket so the next person
  who picks it up sees the clock without doing the maths.

## 4. After recovery
- Re-run the tracker — the ticket should move to Resolved and drop out of
  the breach list; note the actual resolution time against the deadline.
- Log the breach in the weekly SLA report with the reason recorded in step 2.
- If a ticket breached because nobody picked it up, that is a queue problem,
  not an assignee problem — say so in the handover.

## 5. RCA prompts
- Why was the breach only spotted at the 09:20 review? Should the tracker
  run hourly (exit code 2 = page) instead of once a morning?
- Which at-risk tickets became breaches — was the warning window (2h / 25%)
  long enough for a P1 with a 4h target?
- Are the SLA targets themselves realistic for this queue, or is one
  priority breaching every week? A target the team can never meet is a
  process problem, not a performance problem.
- Problem record: link repeat breaches of the same service — one breach is
  an incident, a pattern is a problem.
