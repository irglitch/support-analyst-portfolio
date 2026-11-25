# Runbook — Change Request Readiness Checker (Day 19)

## 1. Verify before you escalate (10 minutes)
- Spot-check the report against the tickets before CAB sees it: open
  CHG-8902 and confirm the rollback trigger really says "TBD" and the
  service-owner approval really is pending. A readiness report that
  disagrees with the ticket system loses the room in the first minute.
- Re-check the window maths by hand on the blocked change: CHG-8904
  needs 50m to implement and 20m to roll back in a 60m window — 70m
  does not fit, so either the window grows or the change waits.
- Confirm the load-test evidence on the high-risk change is real, not
  a ticked box: CHG-8901's note says the pool peaked at 71 of 120 at
  1.5× Monday peak. If the note were empty, treat the tick as
  unproven and ask for the test result before CAB.
- Check the report was run on the latest export — re-run it if any
  ticket changed after the export was taken, and use
  `--change CHG-xxxx` to re-check a single change once its owner says
  the blocker is fixed.

## 2. Escalate with facts, not feelings
Take the ranked action list into CAB and quote the lines that matter:
- **Blocked:** CHG-8902 — rollback trigger "TBD", service-owner
  approval outstanding. CHG-8904 — 70m of work in a 60m window,
  dependencies unchecked.
- **Conditional:** CHG-8903 — notice drafted but not sent, no peer
  review. CAB can approve with those as conditions, or defer a week.
- **Ready:** CHG-8901 (high risk, load tested, trigger defined, CAB
  approved) and CHG-8905 (standard certificate renewal) — say plainly
  that the high-risk change is the best-prepared one in the pack;
  that is the INC-2011 lesson working.
- **The ask:** defer CHG-8902 and CHG-8904 to next week's CAB unless
  the owners clear the blockers before the window; do not approve
  "subject to the trigger being written later" — that is how CHG-8841
  happened.

Escalation path: change manager first (they own the CAB pack), then
the service owners for the blocked changes. Support's role is to
surface the gaps with evidence, not to approve or reject the change.

## 3. Communicate
- Tell the business in plain language: "Two of Thursday's five changes
  are not ready — one has no defined point at which we'd back out,
  and one doesn't fit its own window. The payment pool fix from
  Monday's outage is ready and properly tested."
- Give each blocked owner the exact fix, not a verdict: "write the
  rollback trigger as a measurable condition" and "extend the window
  to 90 minutes or split the index build" are actions; "not ready"
  alone is not.
- Announce the re-check: "fix it and I'll re-run the checker the same
  day" — a blocker that can clear before the window should not have
  to wait a week by default.

## 4. After recovery
- After the window, confirm the ready changes implemented as planned:
  CHG-8901's pool reads 120 and the 30-minute watch was clean;
  CHG-8905's new certificate expiry is live. A change that was
  "ready" but never verified is an open loop.
- Track the deferred changes: CHG-8902 and CHG-8904 return to the
  next CAB only with the blockers cleared — re-run the checker on
  the updated tickets rather than trusting "we fixed it".
- If a conditional change (CHG-8903) was approved with conditions,
  confirm the conditions were actually met — the notice sent, the
  peer review done — and record it on the ticket.

## 5. RCA prompts
- Why did CHG-8902 reach CAB with a "TBD" rollback trigger — is the
  trigger a mandatory field in the change form, or can it be left
  blank until implementation night?
- CHG-8904's window maths failed: does the change form check
  implementation + rollback against the window at submission time, or
  does every CAB repeat this arithmetic by hand?
- CHG-8901 shows the load-test rule working. Is it enforced by the
  process (the Day 18 action item, due 2026-12-04) or did this team
  just do it properly on its own?
- Problem record: if changes keep arriving at CAB with the same two
  gaps (no trigger, window too short), that is a problem to fix in
  the change template, not five separate conversations every week.
