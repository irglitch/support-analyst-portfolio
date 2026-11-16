# Day 10 — Pre-Batch Data Validation Checker

## 🧾 The situation (real-world use case)

**Monday, 09:20.** The overnight settlement batch (batch 8815) is due to
run at 10:00, and Finance has just dropped the staging file — 20
settlement rows for today. Support's job is to validate the file
**before** the batch runs. A bad row inside the batch means a failed run,
a partial settlement and a 10 a.m. incident, with Finance, the batch team
and the business all asking what happened. Checking 20 rows by hand
means eyeballing amounts, dates and account numbers one by one — and
still missing the duplicate that settles the same payment twice.

## 🔧 The fix

`validator.py` loads the staging CSV into SQLite (Python stdlib only)
and runs the checks in `validation.sql`:

- **Duplicate transaction IDs** — the same `txn_id` appearing more than
  once (a re-post that would settle the same payment twice)
- **Missing amount** — a row with no amount at all
- **Negative amount** — a refund-shaped value in a settlement file
- **Zero amount** — a row that settles nothing
- **Unexpected currency** — this batch settles CAD and USD only
- **Future transaction date** — a row dated after the batch date
- **Malformed account number** — must be `ACC-` followed by 4 digits
- **Missing customer ID** — a payment with nobody attached to it
- **Invalid status** — only `settled` / `pending` may enter the batch

A row that fails two rules is still counted once — the report counts
**rows**, not rule hits — so the blocked-row count always adds up to the
file total.

The tool only reads the staging file and reports — it never edits the
file, never deletes a row and never starts the batch. Whether the batch
runs with the bad rows removed, or waits for a corrected file, is
Finance's call; support supplies the evidence.

## ▶️ Run it

```bash
cd projects/day-10-pre-batch-data-validation-checker
python3 validator.py sample_data/staging_settlements.csv --out output/validation_report.md
cat output/validation_report.md
```

The checks themselves live in `validation.sql` — the tool loads the CSV
into a `staging` table and runs each statement, so the SQL is readable
and reusable on its own. (In a real environment the staging data would
come from the landing table the file feed loads into, exported to the
same CSV shape.)

Exit codes: `0` = GO, no blockers (a scheduler can gate the batch on
this), `1` = BLOCKED, bad rows found, `2` = error.

**Result on the sample data:** 20 rows in the file — 10 valid
($1,390.59) and 10 blocked, with all 9 rules failing once each:

| Rule | Bad row |
|---|---|
| Duplicate transaction ID | TXN-4100 (appears twice — would settle $129.99 twice) |
| Missing amount | TXN-4103 |
| Negative amount | TXN-4104 (-$18.75) |
| Unexpected currency | TXN-4105 (EUR — batch settles CAD / USD only) |
| Future transaction date | TXN-4106 (dated 2026-11-17, batch date is 2026-11-16) |
| Malformed account number | TXN-4107 (ACC-10X8) |
| Missing customer ID | TXN-4108 |
| Zero amount | TXN-4109 ($0.00) |
| Invalid status | TXN-4110 (status "error") |

The verdict is 🔴 **BLOCKED — do not run the batch**. The clean rows
are worth $1,390.59; the 10 blocked rows go back to Finance by
transaction ID, and the batch runs only after a corrected file
re-validates clean.

## ✅ Tests

17 unittest tests, all passing — from the project folder and from the
repo root:

```bash
python3 -m unittest discover -s tests -v
```

- Sample-data totals: 20 rows, 10 valid ($1,390.59), 10 blocked,
  9 of 9 rules fired, every bad transaction ID named
- Each rule on its own: duplicate flags both rows, missing / negative /
  zero amount, unexpected currency, future date, malformed account,
  missing customer, invalid status
- A row failing two rules still counts as one blocked row
- Clean rows pass: yesterday's date is fine, USD is allowed,
  `pending` status is allowed

## 🛠 Skills demonstrated

Data validation before a batch run, SQL checks over a staging table
(GROUP BY / HAVING for duplicates, GLOB pattern for account format),
exit-code gating for a scheduler, and reporting bad rows by ID so the
fixing team can act without a fresh investigation.

Practice scenario with sample data, built for this portfolio — not employer work.
