# RUNBOOK — Day 11: Reconciliation Summary Report Generator

## 1. Verify

- Run the tool on today's two files and read the verdict first:
  🟢 RECONCILED means the day can close; ⚠️ BREAKS FOUND means it
  cannot — not yet.
- **Never trust the net difference alone.** In the sample data the net
  difference is only $25.01, but it hides $214.99 of breaks. A small
  net figure can be two large breaks cancelling each other out. Always
  read the break list, not just the totals.
- Check the counts add up: matched + breaks should account for every
  distinct transaction ID across both files (16 matched + 3 breaks =
  19 distinct IDs in the sample data).
- If the tool exits `2`, the files themselves are the problem — a
  missing file, a duplicate transaction ID, or a bad amount. Fix the
  file, don't hand-edit the report.
- Confirm the largest break first: it usually decides whether the
  close call can wait or needs Finance now.

## 2. Escalate (with facts)

- **Amount mismatch (TXN-5203, −$5.00):** escalate to Finance with
  both figures — "source $250.00, ledger $245.00". Ask whether the
  ledger was short-posted, a fee was deducted, or the source amount
  was wrong. Do not guess which side is right.
- **Missing in ledger (TXN-5207, $89.99):** escalate to the batch /
  posting team — the source system has it, the ledger doesn't. Ask
  whether the posting job skipped it or failed partway through.
- **Missing in source (TXN-5210, $120.00):** escalate to Finance and
  the source-system owner together — a posting with no source record
  is the break that most often turns out to be a duplicate posting or
  a manual entry. Ask for the originating record before anyone
  reverses it.
- Escalate each break **by transaction ID**, never as "the totals
  don't match" — an ID gets a fix; a total starts a fresh
  investigation.

## 3. Communicate

- Tell Finance the verdict and the three breaks in one message:
  "3 breaks worth $214.99 — TXN-5203 is $5.00 short in the ledger,
  TXN-5207 ($89.99) never posted, TXN-5210 ($120.00) has no source
  record. Net difference is only $25.01, so the totals alone would
  have hidden this."
- Tell the business the close call is held and why, in one line:
  "Reconciliation found 3 breaks worth $214.99, so the day can't
  close until Finance clears them — 16 of 19 transactions matched
  exactly."
- Give a time, not a shrug: re-running the report takes under a
  minute once corrected files land, so the close can still happen
  the same morning.

## 4. After recovery

- Re-run the tool on the corrected files and keep the new report —
  the day closes only on a 🟢 RECONCILED report, never on a verbal
  "we fixed it".
- If the same break type repeats tomorrow (another missing posting,
  another amount mismatch), raise it as a feed/posting issue: a
  reconciliation break that repeats daily is a source-system or
  batch bug, not a one-off bad row.
- File the report with the day's close pack so a late-settling
  payment has a paper trail back to the break that held it.

## 5. RCA prompts

- Why was TXN-5203 posted $5.00 short — a fee, a rounding rule in
  the posting job, or a manual edit?
- Why did TXN-5207 never reach the ledger — did the posting job
  skip it, or did it fail after the source file was cut?
- Where did TXN-5210 come from — a duplicate posting, a manual
  journal entry, or a transaction from a different day's file?
- Should reconciliation run automatically right after the batch,
  instead of waiting for the 09:20 manual check?
