# Day 11 — Reconciliation Summary Report Generator

## 🧾 The situation (real-world use case)

**Tuesday, 09:20.** The overnight settlement batch has run, and Finance
wants the daily reconciliation summary before the 10:00 close call: do
the source system and the ledger agree on yesterday's settlements?
Comparing two files row by row by hand is slow — and the one row that
doesn't match is exactly the one you miss. Worse, comparing only the
two totals hides the problem: a $5.00 under-posting and a $120.00
extra posting can nearly cancel out, leaving a small net difference
that looks harmless while two real breaks sit underneath it.

## 🔧 The fix

`reconcile_report.py` loads both settlement CSVs (Python stdlib only)
and matches them on transaction ID, classifying every transaction:

- **Matched exactly** — same amount and currency in both systems
- **Amount mismatch** — same `txn_id`, different amount or currency
- **Missing in ledger** — in the source file, never posted to the ledger
- **Missing in source** — in the ledger with no source record

It then totals each file, computes the net difference (ledger −
source), the total value of all breaks, and the single largest break —
and writes a one-page Markdown summary Finance can act on.

Amounts use `Decimal`, not float, so the report's own numbers balance
exactly — a reconciliation report that doesn't add up is worse than
no report.

The tool only reads the two files and reports — it never edits either
file and never posts a correcting entry. Fixing a break (re-post,
reverse, or write-off) is Finance's call; support supplies the
evidence.

## ▶️ Run it

```bash
cd projects/day-11-reconciliation-summary-report-generator
python3 reconcile_report.py sample_data/source_settlements.csv sample_data/ledger_settlements.csv --out output/reconciliation_summary.md
cat output/reconciliation_summary.md
```

Exit codes: `0` = RECONCILED, no breaks (a scheduler can gate the
close call on this), `1` = BREAKS FOUND, `2` = error.

**Result on the sample data:** 18 rows in each file, 16 matched
exactly. The verdict is ⚠️ **BREAKS FOUND — 3 breaks worth $214.99**:

| Break | Detail |
|---|---|
| Amount mismatch | TXN-5203 — source $250.00, ledger $245.00 (difference −$5.00) |
| Missing in ledger | TXN-5207 — $89.99 in the source file, never posted |
| Missing in source | TXN-5210 — $120.00 in the ledger with no source record |

Source total $2,550.19, ledger total $2,575.20 — a net difference of
only $25.01, which is exactly why totals alone are not enough: the
net figure hides $214.99 of breaks. The largest single break is
TXN-5210 at $120.00. The day does not close until Finance clears all
three breaks by transaction ID.

## ✅ Tests

13 unittest tests, all passing — from the project folder and from the
repo root:

```bash
python3 -m unittest discover -s tests
# Ran 13 tests in 0.010s — OK
```

Tests cover: sample-data totals and break counts, the exact mismatch
details, a clean reconcile of identical files, empty files, duplicate
transaction IDs and bad amounts rejected, the report naming every
break, and the CLI exit codes (0 / 1 / 2).

## 🛠 Skills demonstrated

- SQL-style reconciliation thinking in Python (join on transaction ID, classify by match type)
- Exact decimal arithmetic for money — never float for totals
- Report writing a non-technical team (Finance) can act on without a fresh investigation
- Exit-code gating so a scheduler can block the close call on breaks

Practice scenario with sample data, built for this portfolio — not employer work.
