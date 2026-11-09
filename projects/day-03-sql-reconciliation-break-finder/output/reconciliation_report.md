# Reconciliation Report — Billing vs Finance Ledger

**Billing system:** 16 transactions, total **$3,540.23**  
**Finance ledger:** 16 transactions, total **$3,476.00**  
**Difference (billing − ledger):** $64.23  
**Transactions matched and agreeing:** 13  
**Verdict:** ❌ BREAK FOUND — 4 transaction(s) explain a $64.23 difference.

## 1. Billed but never posted (missing from ledger)

| Transaction | Customer | Date | Amount |
|---|---|---|---|
| TXN-2007 | CUST-2210 | 2026-11-08 | $145.00 |

## 2. Posted but never billed (orphan in ledger)

| Transaction | Customer | Date | Amount |
|---|---|---|---|
| TXN-2017 | CUST-3091 | 2026-11-09 | $89.50 |

## 3. Same transaction, different amount

| Transaction | Billing | Ledger | Difference (ledger − billing) |
|---|---|---|---|
| TXN-2003 | $210.00 | $201.00 | -$9.00 |
| TXN-2012 | $75.25 | $75.52 | $0.27 |

## How the difference adds up

- Missing from ledger: $145.00 (1 transaction(s))
- Orphan in ledger: -$89.50 (1 transaction(s))
- Amount mismatches: $8.73 (2 transaction(s))

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
