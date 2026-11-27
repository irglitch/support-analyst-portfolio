# Runbook — Ticket Categorisation Helper (Day 21)

## 1. Verify before you escalate (10 minutes)
- Confirm the hidden P1 is real before the duty manager hears it:
  try a test checkout and watch it fail, and check the error rate
  and the PAY-3002 timeouts on checkout-api. Two independent reports
  (TKT-3101, TKT-3102) plus a failed test checkout is an outage,
  not a logging mistake.
- Confirm the duplicate with your own eyes: both tickets name
  checkout-api, 500s, and the same 08:40 start. If they match, link
  TKT-3102 to TKT-3101 as the master and tell both reporters —
  neither should be worked as a separate incident.
- Spot-check the quieter flags: the settlement file really is
  absent (TKT-3104 — check the SFTP drop before re-routing), and
  the portal really does serve the old certificate (TKT-3108 —
  Day 20 found the renewal sitting in the vault).
- For TKT-3107, reply to the reporter first: which service, what
  symptom, since when, how many users. A categorisation guess on
  "system slow" routes it wrong with confidence.

## 2. Escalate with facts, not feelings
Take the ranked action list to the duty manager and quote the lines
that matter:
- **P1 now:** TKT-3101 — checkout 500s for all customers since
  08:40, revenue stopped, 1,200 affected. It arrived as a P3
  "General" query; the queue order is not the work order.
- **Same incident:** TKT-3102 — link it, keep one master, one
  incident record, one update thread.
- **Re-route today:** TKT-3104 — Batch & File Transfer, P2. The
  settlement batch is blocked until the file lands; every hour in
  the wrong queue is an hour off the batch deadline.
- **P2, deadline Monday:** TKT-3108 — restart the portal onto the
  renewed certificate (Day 20's fix) before the weekend, not
  during it.
- **No action:** TKT-3103, TKT-3105, TKT-3106 are correctly
  categorised — say so, so the queue review takes minutes, not a
  re-read of all eight.

Escalation path: duty manager for the P1 declaration, then the
checkout service owner. Support's role at triage is to get the
right ticket in front of the right team at the right priority —
fast, with the evidence attached.

## 3. Communicate
- Tell the business in plain language: "Checkout is down for all
  customers since 08:40 — it's being worked as a P1 now. The
  settlement file is missing and being chased with the batch team.
  Everything else in the queue is routine."
- Update both outage reporters on the master ticket, so the
  duplicate's reporter is not left thinking their ticket vanished.
- Give each owner the exact fix, not a verdict: "re-route
  TKT-3104 to Batch & File Transfer" is an action; "miscategorised"
  alone is not.

## 4. After recovery
- Re-run the helper after the queue is corrected: a clean run
  (exit 0) is the evidence that triage is done, and it attaches to
  the shift handover.
- Check the P1's clock honestly: the SLA started at 08:40, not at
  09:20 when triage caught it. Record the detection gap on the
  incident — it feeds the RCA.
- When TKT-3107's reporter answers, re-check it with
  `--ticket TKT-3107` and route it on facts, not on the original
  guess.

## 5. RCA prompts
- Why did a revenue-stopping outage arrive as a P3 "General"
  query — is there no impact question on the logging form, or did
  the web team bypass it? A mandatory "who is affected" field
  would have caught this at 08:40.
- Two reports of one outage sat unlinked for 40 minutes: does
  anything match new tickets against open incidents on the same
  service, or does that depend on an analyst noticing?
- The settlement file was miscategorised for the second time
  ("missing again") — is the category list missing a file-transfer
  option at the point of logging, or is training the gap?
- Problem record: if "General" keeps absorbing outages, batch
  failures, and vague reports, the category itself is the problem
  — restrict it, or make triage review of "General" tickets a
  timed SLA of its own.
