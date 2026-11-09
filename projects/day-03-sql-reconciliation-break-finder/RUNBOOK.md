# Runbook — Reconciliation Break (Day 03)

## 1. Verify before you escalate (10 minutes)
- Re-run the finder on **fresh extracts** pulled at the same cutoff time — a
  totals gap caused by one extract being pulled an hour later than the other
  is a timing artefact, not a break. Same cutoff, or the comparison is meaningless.
- Spot-check one break in each system by hand: open TXN-2007 in the billing
  UI and confirm it really has no ledger posting; open TXN-2017 in the ledger
  and confirm it really has no bill.
- Confirm the counts: if both extracts have the same row count but different
  totals, say so — it rules out "a whole batch is missing" and points at
  individual rows (which is what the tool found here).

## 2. Escalate with facts, not feelings
Paste into the ticket / finance email:
- **The gap:** billing $3,540.23 vs ledger $3,476.00 — $64.23, 4 transactions
- **The break table** from the report — transaction IDs, amounts, and which
  side each one is missing from or differs on
- **The proof it's fully explained:** $145.00 − $89.50 + $8.73 = $64.23, and
  13 of 16 transactions match exactly
- **Suggested owners:** missing posting → billing/settlement team (did the
  feed drop TXN-2007?); orphan posting → finance (is TXN-2017 a duplicate
  entry or a bill that never got raised?); amount mismatches → the team that
  keys amounts (TXN-2003 looks like a transposed digit, $210.00 vs $201.00)

Never adjust a total to make the report balance — the break stays open until
each named transaction is corrected at source.

## 3. Communicate
- Tell finance **which** transactions break, not just the size of the gap —
  they can chase 4 rows today; they can't chase "$64.23".
- If month-end close is blocked, give a realistic ETA per break owner and
  update the ticket when each one clears — don't wait for all four.
- Don't tell users or customers anything about this one: it's a back-office
  reconciliation, and no customer-facing balance is wrong until finance says so.

## 4. After recovery
- Re-run the finder on fresh extracts — totals should match to the cent and
  all four break rows should be gone from the report.
- Ask finance to confirm the corrected postings landed in the ledger before
  closing the ticket; a "fixed" break that never posted is the same break.
- File the report with the incident/ticket so the next totals mismatch starts
  from a known-good baseline, not from scratch.

## 5. RCA prompts
- Why did TXN-2007 never post — feed failure, a rejected row nobody noticed,
  or a posting cut off by the batch window?
- Why does the ledger hold a posting (TXN-2017) with no bill — manual entry,
  a duplicate, or a bill raised under a different ID?
- What catches transposed digits (TXN-2003) before posting — a second-person
  check, an amount-tolerance alert, or a same-day recon run?
- Should this recon run **daily and automatically** instead of when finance
  notices? A $64.23 break found the same morning is a 10-minute fix; found
  at month-end it's a blocked close.
