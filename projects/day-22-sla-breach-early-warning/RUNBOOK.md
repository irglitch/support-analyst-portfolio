# Runbook — SLA Breach Early Warning (Day 22)

## 1. Verify before you escalate (10 minutes)
- A forecast is only as honest as the estimate behind it. Before
  the duty manager hears "will breach", confirm INC-3201's 90
  minutes remaining with Sam R directly: what is left, what is it
  waiting on, and is 40% progress real? If the estimate is stale,
  the forecast is fiction in the other direction.
- Confirm the breach is real: INC-3203's 07:00 deadline passed
  with the CRM sync still stuck — check the sync status yourself
  rather than trusting the ticket's "In Progress".
- For the at-risk three, verify the signal, not the label:
  INC-3202 really is waiting on the bank (check the SFTP drop),
  INC-3204 really has had no update in 20 hours, and INC-3206
  really has no owner. Each takes under a minute to confirm.
- Check Sam R's load with your own eyes: the breached ticket and
  both will-breach tickets are all his. That is a staffing fact,
  not a performance comment — frame it that way.

## 2. Escalate with facts, not feelings
Take the ranked report to the duty manager and quote the lines
that carry a deadline:
- **Breached:** INC-3203 — P2, deadline 07:00, 2h 20m over, CRM
  sync still stuck. It needs a recovery plan and a business
  update that states the breach plainly.
- **Breaches at 09:40 unless something changes:** INC-3201 — P1
  checkout, 20m of clock, 90m of work. The honest options are add
  help, cut scope, or declare the coming breach now instead of
  discovering it at 09:41.
- **Breaches at 12:00 on current pace:** INC-3208 — 40m overrun
  forecast with 2h 40m of clock left. This is the one the early
  warning exists for: still saveable.
- **Chase today:** INC-3202 (bank resend — chase the blocker,
  not Priya), INC-3204 (20h without an update at 10% progress),
  INC-3206 (unassigned 18h — assign an owner before anything
  else).
- **No action:** INC-3205, INC-3210, INC-3207 — say so, so the
  weekend check takes minutes.

Escalation path: duty manager for the breach and the P1 forecast,
then the service owners. Support's value here is timing: the same
facts at 11:00 would be a breach report; at 09:20 they are still
decisions.

## 3. Communicate
- Tell the business in plain language: "One ticket has breached
  its target (CRM sync, being recovered now). The checkout P1 is
  forecast to miss its 09:40 target by about an hour unless we
  add help — that call is with the duty manager now. Everything
  else is being chased today."
- Update the breached ticket's reporters first, with the breach
  stated, not softened: a customer who hears it from support
  trusts the next update more.
- Give each owner the exact ask, not a verdict: "reassign
  INC-3208 or add a second pair of hands by 10:30" is an action;
  "at risk" alone is not.

## 4. After recovery
- Re-run the sweep after the actions land: the 11:00 re-check
  (`--now`) is the evidence the warnings were acted on, and it
  attaches to the weekend handover.
- Record the forecast accuracy honestly: did INC-3201 finish near
  10:50? A forecast checked against reality is how the estimates
  — and the thresholds — get better.
- The breach that already happened (INC-3203) still needs its
  RCA input: when did it first become forecastable, and why did
  no sweep catch it at 06:00?

## 5. RCA prompts
- INC-3203 breached at 07:00 and was found at 09:20: is there no
  sweep before the morning check, or did nobody own the weekend
  queue overnight? An hourly automated run (exit code 1/2 to the
  on-call channel) closes that gap without heroics.
- INC-3206 sat unassigned for 18 hours: does assignment depend
  on someone noticing, or is there an unassigned-aging alert?
  Unassigned time should be its own SLA.
- INC-3204's estimate ("30m remaining", 10% progress, no update
  in 20h) was never challenged: are stale estimates refreshed on
  a cadence per priority, or only when someone asks?
- One analyst held the breach and both forecasts: is weekend
  cover staffed for the queue's actual shape, or for its average?
  Problem record: if overload predicts breaches, workload belongs
  in the early-warning sweep permanently — as it now is.
