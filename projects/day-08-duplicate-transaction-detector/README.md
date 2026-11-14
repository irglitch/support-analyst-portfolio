# Day 08 — Duplicate Transaction Detector

## 💰 The situation (real-world use case)

**Friday, 09:20.** Finance calls: yesterday's total looks too high, and a
customer has rung in saying they were charged twice for the same order.
The extract has 22 transactions totalling **$2,845.50** — but are all 22
real charges, or did something post twice? Eyeballing the file won't
catch it: the re-posted rows are identical, and the double-click pair has
*different* transaction IDs, so a simple "find the repeated ID" check
misses it entirely. Meanwhile the customer is waiting for an answer and
finance can't close the day until the duplicate amount is known.

## 🔧 The fix

`duplicate_detector.py` loads the transaction extract into SQLite (Python
stdlib only) and runs the queries in `duplicates.sql`:

- **Headline totals** — rows posted, unique transaction IDs, total value
- **Exact duplicates** — the same `txn_id` posted more than once
  (`GROUP BY txn_id HAVING COUNT(*) > 1`) — the classic batch re-post
  or payment retry
- **Near duplicates** — same customer, same amount, same day, within
  **10 minutes** of each other, different `txn_id` (self-join on
  customer + amount + day with a time window) — the classic
  double-clicked checkout or retry that generated a new ID

Amounts are stored as **integer cents** in SQLite, so totals are exact —
no float rounding on money, ever.

The tool also shows its work on the rows it did **not** flag, so the
report is defensible: TXN-3014 is the same customer and amount as
TXN-3004 but 5 hours later (a legitimate repeat purchase, outside the
window), and TXN-3017 is the same amount but a different customer.

## ▶️ Run it

```bash
cd projects/day-08-duplicate-transaction-detector
python3 duplicate_detector.py sample_data/transactions.csv --out output/duplicate_report.md
cat output/duplicate_report.md
```

The queries themselves live in `duplicates.sql` — the tool loads the CSV
into a `transactions` table and runs each statement in order, so the SQL
is readable and reusable on its own.

Exit codes: `0` = no duplicates, `1` = duplicates found (a scheduler can
page on this), `2` = error.

**Result on the sample data:** 22 rows posted, 20 unique transaction
IDs, total **$2,845.50** — with **3 extra charges worth $208.73**:

| Duplicate | Transaction | Detail |
|---|---|---|
| Exact re-post | TXN-3001 | $129.99 posted twice (same ID, same second) |
| Exact re-post | TXN-3005 | $18.75 posted twice (same ID, same second) |
| Near duplicate | TXN-3004 / TXN-3010 | $59.99 charged twice, 147 seconds apart — double-click |

$129.99 + $18.75 + $59.99 = **$208.73** at risk. The true day's value
is $2,845.50 − $208.73 = **$2,636.77** across 19 genuine charges.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

SQL (GROUP BY / HAVING, self-join, date and time functions) · Duplicate
detection & data validation · Money handling (integer cents, no float
rounding) · Python + SQLite · Finance-facing communication · Support
documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
