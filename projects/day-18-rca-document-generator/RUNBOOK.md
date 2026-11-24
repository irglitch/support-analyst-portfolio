# Runbook — RCA Document Generator (Day 18)

## 1. Verify before you escalate (10–15 minutes)
- Re-read the timeline against the sources before the document goes
  anywhere: the change record for CHG-8841 (02:15, pool 200 → 50),
  the health-check probe log from 09:02, and the ticket timestamps.
  A timeline that disagrees with the logs will be the first thing the
  review picks apart.
- Re-run the completeness check — `python3 rca_generator.py
  sample_data/incident.json` must exit 0 and stamp FINAL. A DRAFT
  that reaches the business review is worse than a late RCA: it tells
  the room the team didn't check its own work.
- Check the root cause against the fix that actually worked: the pool
  was raised back to 200 and checkout recovered. If the "root cause"
  doesn't explain why that fix worked, it isn't the root cause yet.
- Verify the impact numbers independently — the 1,240 failed
  checkouts and the $38,450 figure come from the checkout logs and
  the order system, not from memory. And re-run the Day 08 duplicate
  check if anything changed after closure: "no double-charges" is a
  claim the business will repeat, so it has to stay true.
- Challenge the 5 whys: each "why" must answer the one above it, and
  the last one must point at something fixable (a process gap, not a
  person). "Because someone made a mistake" is not a root cause —
  "because the change process has no load check" is.

## 2. Escalate with facts, not feelings
Attach the RCA to the incident ticket and quote the lines that matter:
- **What:** INC-2011, P1, checkout 500s, 09:02–10:47 (1h 45m),
  1,240 failed checkouts, ~$38,450 interrupted
- **Why:** CHG-8841 cut the connection pool 200 → 50 with no load
  test against Monday peak traffic; no rollback trigger on the setting
- **Honest miss:** the P1 breached its 60-minute SLA by 45 minutes,
  and there was no pool-exhaustion runbook — say so plainly, don't
  bury it in the action items
- **What is verified:** 0 double-charges (Day 08 check), error rate
  back under 1% by 10:31, backlog cleared 10:47
- **What is still open:** 4 action items, earliest due 2026-11-26
  (runbook), latest 2026-12-04 (change-process load check)

Escalation path: duty manager first (they own the review), then the
change manager (the load-check action is theirs) and the platform team
(the 80% pool alert). **Do not name a person as the root cause** — the
RCA is about the process that let the change through, and blaming an
individual in a business document kills the next honest incident report.

## 3. Communicate
- Tell the business in plain language: "checkout was down for about
  an hour and three quarters on Monday morning because a change
  overnight shrank the database connection pool; it's fixed, nobody
  was charged twice, and here are the four things we're doing so it
  doesn't happen again."
- Present the timeline, not just the conclusion — the review trusts a
  document that shows its working (detection at 09:02, cause found
  at 09:58, fix at 10:12) more than one that just asserts a cause.
- Give the next update time for the action items: "weekly check until
  all four are closed; if the pool alert (due 27th) slips, it comes
  back to the duty manager."

## 4. After recovery
- Track the four action items to closure — an RCA whose actions are
  never done is a document, not a fix. Check weekly; the runbook
  (due 2026-11-26) and the pool alert (due 2026-11-27) are the ones
  that protect the next Monday morning.
- When the pool alert goes live, test it: drive pool usage to 80% in
  a test window and confirm it fires. An untested alert is a line in
  a document, not a control.
- Keep the RCA linked from the ticket and from the Day 07 error-code
  knowledge base — the next time checkout 500s appear, the first
  search should find this RCA, not start a fresh investigation.

## 5. RCA prompts
- Why did a cost-saving change reach production with no load test —
  is the change process missing the check, or did the requester skip
  a check that exists?
- Why did the pool setting have no rollback criteria — are other
  configuration changes in the same position?
- Would the 80% pool alert have caught this before customers did, and
  what other thresholds (disk, latency, error rate) are running
  without an alert?
- The P1 breached by 45 minutes: was the SLA realistic for a fault
  with no runbook, or was the delay in the 23 minutes spent
  confirming the cause?
- Problem record: if configuration changes keep causing outages, this
  is a problem to fix (change-process controls), not an incident to
  repeat — and the next RCA should be able to say "this control
  caught it".
