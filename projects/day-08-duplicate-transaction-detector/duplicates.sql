-- Day 08 — Duplicate Transaction Detector
-- Run against a `transactions` table loaded from the daily extract:
--   txn_id TEXT, customer_id TEXT, txn_timestamp TEXT ('YYYY-MM-DD HH:MM:SS'),
--   amount_cents INTEGER, status TEXT
-- Amounts are stored as integer cents so totals are exact.

-- 1. Headline totals: rows posted, unique transaction IDs, total value.
SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT txn_id) AS unique_txn_ids,
       SUM(amount_cents) AS total_cents
FROM transactions;

-- 2. Exact duplicates: the same txn_id posted more than once.
--    Classic cause: a batch job or payment retry re-posted the same row.
SELECT txn_id, customer_id, amount_cents, COUNT(*) AS times_posted,
       MIN(txn_timestamp) AS first_seen, MAX(txn_timestamp) AS last_seen
FROM transactions
GROUP BY txn_id
HAVING COUNT(*) > 1
ORDER BY txn_id;

-- 3. Near duplicates: different txn_id, same customer, same amount,
--    same day, within 10 minutes of each other.
--    Classic cause: a customer double-clicking checkout, or a retry that
--    generated a new ID. The 10-minute window keeps legitimate repeat
--    purchases (same customer, same amount, hours apart) out of the list.
SELECT a.txn_id AS txn_a, b.txn_id AS txn_b,
       a.customer_id, a.amount_cents,
       a.txn_timestamp AS time_a, b.txn_timestamp AS time_b,
       CAST(ABS(strftime('%s', b.txn_timestamp)
                - strftime('%s', a.txn_timestamp)) AS INTEGER) AS seconds_apart
FROM transactions a
JOIN transactions b
  ON a.customer_id = b.customer_id
 AND a.amount_cents = b.amount_cents
 AND date(a.txn_timestamp) = date(b.txn_timestamp)
 AND a.txn_id < b.txn_id
 AND ABS(strftime('%s', b.txn_timestamp)
         - strftime('%s', a.txn_timestamp)) <= 600
ORDER BY a.txn_timestamp;
