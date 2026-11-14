# Runbook — Duplicate Transactions (Day 08)

## 1. Verify before you escalate (10 minutes)
- Re-run the detector on a **fresh extract** pulled at the same cutoff —
  a duplicate that only exists in a stale extract is a timing artefact,
  not a double charge. Same cutoff, or the comparison is meaningless.
- Spot-check one duplicate in each system by hand: open TXN-3001 in the
  payment/billing UI and confirm it really posted twice; open TXN-3010
  and confirm it is a separate charge to the same customer, not a
  display glitch.
- Confirm the customer impact before promising anything: has CUST-104
  actually been charged twice on their card/bank statement, or did only
  the internal extract double-count it? The refund path depends on the
  answer — never promise a refund from the extract alone.

## 2. Escalate with facts, not feelings
Paste into the ticket / finance email:
- **The headline:** 22 rows posted, 20 unique IDs — 3 extra charges,
  **$208.73** at risk; true day value $2,636.77
- **The duplicate table** from the report — transaction IDs, customers,
  amounts, and whether each is an exact re-post or a near duplicate
- **The proof it's fully explained:** $129.99 + $18.75 + $59.99 =
  $208.73, and the two rows the tool deliberately did *not* flag
  (TXN-3014, 5 hours later; TXN-3017, different customer) so finance
  knows the list is checked, not just long
- **Suggested owners:** exact re-posts (TXN-3001, TXN-3005) → the team
  that owns the batch job / payment retry (did the job run twice, or
  did a retry re-post?); near duplicate (TXN-3004 / TXN-3010) →
  checkout/payments team (double-click protection? idempotency key?)

Never delete or edit a posted transaction to make the report balance —
each duplicate stays open until finance reverses or refunds it at source.

## 3. Communicate
- Tell the customer **which** charge is the duplicate and what happens
  next (refund / reversal, and when) — "you were charged twice" is only
  useful with the amount ($59.99) and the date.
- Tell finance the **exact** rows to reverse, not just "$208.73" — they
  can reverse 3 named transactions today; they can't reverse a total.
- If the duplicate total is material, say so plainly and give an ETA
  per owner — don't wait for all three to clear before updating the ticket.

## 4. After recovery
- Re-run the detector on fresh extracts — the report should come back
  ✅ CLEAN, with the reversed transactions gone or marked as reversed.
- Ask finance to confirm the refunds/reversals actually landed before
  closing the ticket; a "fixed" duplicate that never refunded is the
  same duplicate.
- File the report with the incident/ticket so the next "total looks too
  high" starts from a known-good baseline, not from scratch.

## 5. RCA prompts
- Why did TXN-3001 and TXN-3005 post twice — did the batch job run
  twice, did a retry fire after a timeout, or did the file get
  re-sent?
- Why did the double-click (TXN-3004 / TXN-3010) create two charges —
  is there no idempotency key on the checkout, and should the button
  disable after the first click?
- What catches a duplicate **before** the customer calls — a daily
  duplicate check like this one, a unique constraint on `txn_id`, or
  an amount-tolerance alert on the daily total?
- Should this check run **daily and automatically** instead of when
  finance notices the total looks high? A $208.73 duplicate found the
  same morning is a same-day refund; found at month-end it's a
  customer complaint and a blocked close.
