# Runbook — Database Locks / Slow Sessions (Day 09)

## 1. Verify before you escalate (10 minutes)
- Re-pull the session snapshot **now** — a blocking chain from a stale
  snapshot may already be gone, and a chain that only exists in a stale
  snapshot is a timing artefact, not an incident. Same snapshot time, or
  the comparison is meaningless.
- Check whether the blocker is actually still running, or already
  finished: SESS-101's settlement update may complete on its own in the
  next minute, and the blocked sessions then clear without anyone doing
  anything. A blocker that finished 30 seconds ago needs no escalation.
- Confirm the user impact before promising anything: are checkouts
  actually failing, or just slow? SESS-104's payment insert waiting
  10m 40s is a customer-facing delay; SESS-107's balance read is a
  reporting delay. The urgency — and who gets paged — depends on which.
- Never kill a session from the support desk. Killing SESS-101 would
  roll back 42 minutes of settlement work and could leave the batch
  half-applied; killing SESS-102 would roll back a paid order. That call
  belongs to the DBA team, with the business impact weighed first.

## 2. Escalate with facts, not feelings
Paste into the ticket / DBA email:
- **The headline:** 🔴 BLOCKING CHAIN — 2 blockers holding up 4
  sessions; longest wait 10m 40s (SESS-104, payment insert)
- **The chains:** SESS-101 (overnight settlement, 42m 0s, blocking 3) and
  SESS-102 (checkout-api idle in transaction, 18m 0s, blocking 1)
- **The blocked sessions** from the report — session IDs, what each is
  trying to run, and how long each has waited
- **The proof it's fully explained:** every blocked session points at one
  of the two blockers, and the reporting query (SESS-103, 12m 0s) blocks
  nobody — so the fix is the two chains, not "the database is slow"
- **Suggested owners:** SESS-101 → the batch/settlement team (why has
  the overnight batch run 42 minutes into the morning?); SESS-102 →
  the checkout team (why did the app leave a transaction open for
  18 minutes — missing commit, or a hung API call?)

## 3. Communicate
- Tell the affected users / business **which** sessions are blocked and
  what they are waiting on — "checkouts are delayed because the
  overnight settlement batch is holding the transactions table" is
  actionable; "the database is slow" is not.
- Give an ETA per owner — the batch team can say when SESS-101 finishes,
  the DBA team can say whether SESS-102 will be killed — don't wait for
  both chains to clear before updating the ticket.
- If checkouts are failing (not just slow), say so plainly and give the
  customer-facing impact: how many payments are stuck, and since when.

## 4. After recovery
- Re-run the checker on a fresh snapshot — the report should come back
  ✅ HEALTHY, with no blocked sessions and no session over 10 minutes.
- Confirm with the business that checkouts are completing again before
  closing the ticket; a cleared lock with payments still stuck is the
  same incident.
- File the report with the incident/ticket so the next "app is slow"
  starts from a known-good baseline, not from scratch.

## 5. RCA prompts
- Why did the overnight settlement batch (SESS-101) run 42 minutes into
  the morning — did it start late, did the data volume grow, or is the
  update itself slow (missing index, full-table scan)?
- Why did SESS-102 sit idle in a transaction for 18 minutes — did the
  app fail to commit after the update, is a downstream call hanging, or
  is a connection being held by a pool that never returns it?
- Why did the reporting query (SESS-103) run 12 minutes during business
  hours — should heavy reports run off-peak, or against a read replica?
- What catches a blocking chain **before** users call — a scheduled
  session check like this one every 15 minutes, a lock-wait alert over
  5 minutes, or a batch-overrun alert when the settlement job passes its
  expected finish time?
- Should the batch and the checkout traffic be separated — different
  connection pools, or the batch running against a window where it
  cannot block live checkouts?
