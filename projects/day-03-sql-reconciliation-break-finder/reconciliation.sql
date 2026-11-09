-- Day 03 — SQL Reconciliation Break Finder
-- Tables (loaded from the CSV extracts by recon_break_finder.py):
--   billing        (txn_id TEXT, customer_id TEXT, txn_date TEXT,
--                   amount_cents INTEGER, status TEXT)
--   finance_ledger (txn_id TEXT, customer_id TEXT, posting_date TEXT,
--                   amount_cents INTEGER, status TEXT)
-- Amounts are stored as integer cents so totals are exact — no float rounding.
-- Each statement ends with a semicolon; the Python tool runs them in order.

-- 1. Totals per system — the first thing finance asks for.
SELECT 'billing' AS system, COUNT(*) AS txn_count, SUM(amount_cents) AS total_cents
FROM billing;
SELECT 'ledger' AS system, COUNT(*) AS txn_count, SUM(amount_cents) AS total_cents
FROM finance_ledger;

-- 2. Billed but never posted — in billing, missing from the ledger.
SELECT b.txn_id, b.customer_id, b.txn_date, b.amount_cents
FROM billing b
LEFT JOIN finance_ledger f ON f.txn_id = b.txn_id
WHERE f.txn_id IS NULL
ORDER BY b.txn_id;

-- 3. Posted but never billed — in the ledger, missing from billing.
SELECT f.txn_id, f.customer_id, f.posting_date, f.amount_cents
FROM finance_ledger f
LEFT JOIN billing b ON b.txn_id = f.txn_id
WHERE b.txn_id IS NULL
ORDER BY f.txn_id;

-- 4. Same transaction, different amount — the classic transposed-digit break.
SELECT b.txn_id,
       b.amount_cents AS billing_cents,
       f.amount_cents AS ledger_cents,
       f.amount_cents - b.amount_cents AS diff_cents
FROM billing b
JOIN finance_ledger f ON f.txn_id = b.txn_id
WHERE b.amount_cents <> f.amount_cents
ORDER BY b.txn_id;

-- 5. Matched and agreeing — the clean majority, for the report's sanity check.
SELECT COUNT(*) AS matched_agreeing
FROM billing b
JOIN finance_ledger f ON f.txn_id = b.txn_id
WHERE b.amount_cents = f.amount_cents;
