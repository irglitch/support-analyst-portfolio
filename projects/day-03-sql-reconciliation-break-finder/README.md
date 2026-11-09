# Day 03 — SQL Reconciliation Break Finder

## 💰 The situation (real-world use case)

**Monday, 09:40.** Finance calls: the daily totals don't match. The billing system
says **$3,540.23** for yesterday, the finance ledger says **$3,476.00** — a
**$64.23** gap, and month-end close is blocked until it's explained. Both extracts
have 16 transactions, so "just count them" doesn't help: the counts agree and the
totals don't. Somebody has to find *which* transactions break, not just that a
break exists — eyeballing two 16-row spreadsheets takes an hour and still misses
the transposed digit.

## 🔧 The fix

`recon_break_finder.py` loads both CSV extracts into SQLite (Python stdlib only)
and runs the queries in `reconciliation.sql`:

- **Totals + counts per system** — the headline numbers finance asked for
- **Billed but never posted** — transactions in billing with no ledger row
  (`LEFT JOIN ... WHERE ledger.txn_id IS NULL`)
- **Posted but never billed** — orphan postings in the ledger with no bill
- **Same transaction, different amount** — the classic transposed-digit break
- **Matched and agreeing** — the clean majority, so the report proves the
  scope of the problem is small

Amounts are stored as **integer cents** in SQLite, so totals are exact —
no float rounding on money, ever.

## ▶️ Run it

```bash
cd projects/day-03-sql-reconciliation-break-finder
python3 recon_break_finder.py sample_data/billing_extract.csv sample_data/finance_ledger.csv --out output/reconciliation_report.md
cat output/reconciliation_report.md
```

The queries themselves live in `reconciliation.sql` — the tool loads the CSVs
into `billing` and `finance_ledger` tables and runs each statement in order,
so the SQL is readable and reusable on its own.

**Result on the sample data:** billing **$3,540.23** vs ledger **$3,476.00** —
a **$64.23** break explained by exactly **4 transactions**:

| Break | Transaction | Detail |
|---|---|---|
| Billed, never posted | TXN-2007 | $145.00 missing from the ledger |
| Posted, never billed | TXN-2017 | $89.50 orphan in the ledger |
| Amount mismatch | TXN-2003 | billed $210.00, posted $201.00 (transposed digits) |
| Amount mismatch | TXN-2012 | billed $75.25, posted $75.52 |

$145.00 − $89.50 + $8.73 = **$64.23** — the break is fully explained, and
13 of 16 transactions match exactly, so this is four bad rows, not a broken feed.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

SQL (JOINs, LEFT JOIN anti-pattern, aggregation) · Reconciliation & data
validation · Money handling (integer cents, no float rounding) · Python + SQLite ·
Finance-facing communication · Support documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
