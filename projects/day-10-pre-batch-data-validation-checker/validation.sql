-- Day 10 — Pre-Batch Data Validation Checker
-- Each statement is one validation rule over the staging table.
-- The tool loads the staging CSV into `staging` first, then runs these
-- in order. Batch date, allowed currencies and allowed statuses are
-- passed in as parameters (:batch_date, :currencies, :statuses) by the
-- Python tool; the literals below are the defaults for batch 8815.

-- 1. Headline counts
SELECT COUNT(*) AS total_rows FROM staging;

-- 2. Duplicate transaction IDs (same txn_id appearing more than once)
SELECT txn_id, COUNT(*) AS occurrences
FROM staging
GROUP BY txn_id
HAVING COUNT(*) > 1;

-- 3. Missing amount
SELECT txn_id, customer_id, amount
FROM staging
WHERE amount IS NULL OR TRIM(amount) = '';

-- 4. Negative amount
SELECT txn_id, customer_id, amount
FROM staging
WHERE amount IS NOT NULL AND TRIM(amount) <> ''
  AND CAST(amount AS REAL) < 0;

-- 5. Zero amount
SELECT txn_id, customer_id, amount
FROM staging
WHERE amount IS NOT NULL AND TRIM(amount) <> ''
  AND CAST(amount AS REAL) = 0;

-- 6. Unexpected currency (this batch settles CAD and USD only)
SELECT txn_id, customer_id, currency
FROM staging
WHERE currency NOT IN ('CAD', 'USD');

-- 7. Transaction date after the batch date (future-dated rows)
SELECT txn_id, customer_id, txn_date
FROM staging
WHERE txn_date > '2026-11-16';

-- 8. Malformed account number (must be ACC- followed by 4 digits)
SELECT txn_id, customer_id, account_no
FROM staging
WHERE account_no NOT GLOB 'ACC-[0-9][0-9][0-9][0-9]';

-- 9. Missing customer ID
SELECT txn_id, amount, account_no
FROM staging
WHERE customer_id IS NULL OR TRIM(customer_id) = '';

-- 10. Invalid status (only settled / pending may enter the batch)
SELECT txn_id, customer_id, status
FROM staging
WHERE status NOT IN ('settled', 'pending');

-- 11. Valid-row total (rows with none of the above problems)
-- Computed by the tool from the flagged txn_ids, not by SQL alone,
-- so a row with two problems is still counted once.
