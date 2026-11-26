# Runbook — Deployment Verification Checker (Day 20)

## 1. Verify before you escalate (10 minutes)
- Spot-check the failures against the live systems before the change
  manager hears them: query `search-03` directly and confirm it really
  reports v4.7.2, and read the portal's live certificate expiry with
  your own eyes (2026-12-10). A verification report that disagrees
  with the live system loses the room in the first minute.
- Reproduce the billing smoke failure once by hand — export the test
  invoice and watch the HTTP 500 — and confirm the 6.4% error rate is
  billing-api's, over the post-deployment window, not a stale
  dashboard figure from before 22:57.
- Confirm the observations are fresh: if an owner fixed something
  after the snapshot was taken, re-run with
  `--deployment CHG-xxxx` rather than arguing from a stale report.
- Check the verified changes really are closable: CHG-8852's
  `retry_limit = 5` reads back on both instances and the test file
  posted — that ticket can close. CHG-8851 closes with the 11-minute
  window overrun recorded on it.

## 2. Escalate with facts, not feelings
Take the ranked action list to the change manager and quote the lines
that matter:
- **Roll back now:** CHG-8854 — smoke test HTTP 500 and error rate
  6.4% against a 5.0% rollback trigger. The change's own plan defines
  this condition; the decision is already made, it just needs
  executing. Flag off, then re-verify.
- **Fix or back out:** CHG-8853 — `search-03` still on v4.7.2. Either
  complete the deployment to that instance or roll the other two back;
  a mixed fleet is the worst of both.
- **Finish the job:** CHG-8855 — new certificate is in the vault, the
  endpoint serves the old one (expires 2026-12-10). Restart the portal
  onto the new certificate and re-check the live expiry; this is a
  small fix with a hard deadline behind it.
- **Close:** CHG-8851 (overrun recorded), CHG-8852, and CHG-8856 —
  the held index correctly stayed out, so its ticket closes as
  deferred, not implemented.

Escalation path: change manager first (they own ticket closure), then
the service owners for the failed changes. Support's role is to prove
what is live, not to deploy or roll back.

## 3. Communicate
- Tell the business in plain language: "Three of last night's six
  changes are verified and closing. One is being rolled back because
  invoice export is erroring, one search server missed the update, and
  the portal certificate renewal needs a restart to take effect."
- Give each owner the exact fix, not a verdict: "deploy v5.0.0 to
  search-03" and "restart the portal and confirm the live expiry
  reads 2027" are actions; "failed verification" alone is not.
- Announce the re-check: "fix it and I'll re-run the checker the same
  morning" — a failure that clears before the 10:00 batch should not
  wait for tomorrow's report.

## 4. After recovery
- After each fix, re-run `--deployment CHG-xxxx` and attach the clean
  result to the ticket before closing it: CHG-8854 back under its
  trigger with the flag off (or fixed and re-smoked), CHG-8853 on
  v5.0.0 everywhere, CHG-8855 serving the new expiry.
- Confirm the rollback itself verified: a rolled-back change is
  another deployment — version and config read back at the previous
  values, error rate back under the warning level.
- Tonight's window gets the same treatment tomorrow morning: CHG-8901
  (the INC-2011 pool fix, Day 19) closes only when the pool reads 120
  on every instance and the test checkout passes — readiness before
  CAB, verification after the window.

## 5. RCA prompts
- Why did `search-03` miss the deployment while the tool reported
  success — does the deployment pipeline verify each instance, or
  does it trust the first success response?
- CHG-8854's flag went live without its template: was the smoke test
  part of the deployment pipeline, or only a morning-after check? A
  trigger breached at 22:57 should not wait until 09:20 to be seen.
- CHG-8855 renewed the certificate but never restarted the service:
  is "restart and read back the live expiry" a step in the standard
  renewal procedure (Day 15 flagged this expiry pattern), or does it
  depend on the engineer remembering?
- Problem record: if "deployment succeeded" keeps meaning three
  different things (partial fleet, flag without assets, cert in vault
  not live), that is a problem to fix in the deployment pipeline's
  definition of done, not six separate conversations every week.
