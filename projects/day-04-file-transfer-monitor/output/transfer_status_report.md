# File Transfer Status Report

**Manifest:** `expected_files.csv`  
**Checked at:** 07:30  
**Overall status:** 🔴 ALERT — 2 file(s) missing or empty — including CRITICAL: settlement_20261110.csv  
**Files checked:** 4 · OK 1 · LATE 1 · MISSING 1 · EMPTY 1 · SMALL 0

## Expected files

| File | Expected by | Received | Size | Status | Source |
|---|---|---|---|---|---|
| `settlement_20261110.csv` | 07:00 | — | — | **MISSING** | Payment processor (SFTP) |
| `customer_feed_20261110.csv` | 06:30 | 06:12 | 651 B | **OK** | CRM nightly export |
| `rates_20261110.csv` | 06:00 | 06:47 | 249 B | **LATE** | Rates service |
| `audit_log_20261110.csv` | 07:00 | 07:05 | 0 B | **EMPTY** | Application server |

## What needs action

- **MISSING** — `settlement_20261110.csv` (CRITICAL): No arrival recorded in the transfer log.
  Impact: Daily settlement — finance reconciliation and the downstream batch are blocked without it
- **LATE** — `rates_20261110.csv`: Arrived 06:47, 06:00 was the deadline.
  Impact: FX rates used by billing calculations
- **EMPTY** — `audit_log_20261110.csv`: Zero-byte file — transfer failed or source sent nothing.
  Impact: Overnight audit trail for compliance review

## Unexpected files (arrived but not in the manifest)

- `promo_codes_20261110.csv` — confirm with the sender whether this is a new feed to add to the manifest or a misdirected file.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
