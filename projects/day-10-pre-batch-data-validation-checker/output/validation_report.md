# Pre-Batch Data Validation — Batch 8815

**Batch date:** 2026-11-16  ·  **Staging file:** staging_settlements.csv

## Verdict: 🔴 BLOCKED — do not run the batch

- **Rows in file:** 20
- **Valid rows:** 10 (total $1,390.59)
- **Blocked rows:** 10
- **Rules failed:** 9 of 9

## Bad rows — send these back to Finance

- **Duplicate transaction ID:** TXN-4100 (2 rows)
- **Missing amount:** TXN-4103 (1 row)
- **Negative amount:** TXN-4104 (1 row)
- **Zero amount:** TXN-4109 (1 row)
- **Unexpected currency (batch settles CAD / USD only):** TXN-4105 (1 row)
- **Future transaction date (after batch date):** TXN-4106 (1 row)
- **Malformed account number (must be ACC- + 4 digits):** TXN-4107 (1 row)
- **Missing customer ID:** TXN-4108 (1 row)
- **Invalid status (only settled / pending may enter the batch):** TXN-4110 (1 row)

Fix the rows above and re-validate before the 10:00 run. Do not run the batch on the file as it stands — a duplicate transaction ID would settle the same payment twice, and a missing or negative amount would fail the batch mid-run.
