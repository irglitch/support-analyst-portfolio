# Runbook — Pre-Batch Data Validation (Day 10)

## 1. Verify before you escalate (10 minutes)
- Re-run the validator on the **latest** staging file — Finance may
  already have sent a corrected version, and a report from a stale file
  is a timing artefact, not a blocker. Same file name, or the comparison
  is meaningless.
- Check whether the batch date is right: the future-date rule compares
  against the batch date you pass in (`--batch-date`). A file dated
  2026-11-17 is only "future" if the batch really runs on 2026-11-16 —
  confirm the batch schedule before calling it bad.
- Confirm the currency rule with Finance: this batch settles CAD and USD
  only. EUR is a real currency, not a typo — it is blocked because the
  batch cannot settle it, not because the value is wrong.
- Never edit the staging file yourself, and never delete a bad row to
  make the file pass. A deleted row is a lost payment; the row goes back
  to Finance to fix at source, with its transaction ID attached.

## 2. Escalate with facts, not feelings
Paste into the ticket / Finance email:
- **The headline:** 🔴 BLOCKED — 10 of 20 rows fail validation for
  batch 8815; valid rows total $1,390.59; do not run the 10:00 batch on
  this file
- **The bad rows:** TXN-4100 (duplicate — would settle $129.99 twice),
  TXN-4103 (missing amount), TXN-4104 (negative -$18.75),
  TXN-4105 (EUR), TXN-4106 (future-dated 2026-11-17),
  TXN-4107 (account ACC-10X8), TXN-4108 (no customer),
  TXN-4109 ($0.00), TXN-4110 (status "error")
- **The proof it's fully explained:** 10 valid rows + 10 blocked rows
  = all 20 rows in the file, and every rule that fired names its rows —
  so the fix is these 10 rows, not "the file is bad"
- **Suggested owners:** Finance / the file feed team (source-system
  extract produced the duplicate, the blank amount and the bad status);
  the batch team only needs to know the 10:00 run is held

## 3. Communicate
- Tell Finance **which** rows are bad and **why each one** fails — "TXN-4100
  appears twice" gets a fix; "the file failed validation" starts a fresh
  investigation.
- Tell the business the batch is held and why, in one line: "10 of 20
  settlement rows failed pre-batch checks, so the 10:00 run is held
  until Finance sends a corrected file — the $1,390.59 of clean rows is
  unaffected."
- Give a time, not a shrug: re-validation takes under a minute once the
  corrected file lands, so the batch can still run the same morning.

## 4. After recovery
- Re-run the validator on the corrected file and keep the new report —
  the batch runs only on a 🟢 GO report, never on a verbal "we fixed it".
- If the same rule fires again tomorrow (another duplicate, another
  blank amount), raise it as a feed-quality issue: a validation failure
  that repeats daily is a source-system bug, not a one-off bad row.
- Record the blocked transaction IDs in the incident log so a payment
  that settles late has a paper trail back to this check.

## 5. RCA prompts
- Where did the duplicate TXN-4100 come from — a re-sent file, a
  double-click in the source system, or a retry that posted twice?
- Why did a row with no amount and a row with status "error" reach the
  staging file at all — is there no validation at the feed?
- Should the EUR row have been routed to a different batch instead of
  this one, and who decides that?
