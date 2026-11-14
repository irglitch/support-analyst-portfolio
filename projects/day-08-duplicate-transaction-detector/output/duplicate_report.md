# Duplicate Transaction Report

**Transactions in extract:** 22  
**Unique transaction IDs:** 20  
**Total value posted:** $2,845.50  
**Duplicate extra charges:** 3  
**Amount at risk:** $208.73  
**Verdict:** 🔴 DUPLICATES FOUND — 3 extra charge(s), $208.73 at risk.

## 1. Exact duplicates — same transaction ID posted more than once

| Transaction | Customer | Amount | Times posted | First seen | Last seen |
|---|---|---|---|---|---|
| TXN-3001 | CUST-101 | $129.99 | 2 | 2026-11-13 08:12:04 | 2026-11-13 08:12:04 |
| TXN-3005 | CUST-105 | $18.75 | 2 | 2026-11-13 10:20:33 | 2026-11-13 10:20:33 |

## 2. Near duplicates — same customer, amount and day, within 10 minutes

| First charge | Second charge | Customer | Amount | Seconds apart |
|---|---|---|---|---|
| TXN-3004 (2026-11-13 10:02:10) | TXN-3010 (2026-11-13 10:04:37) | CUST-104 | $59.99 | 147 |

## How the amount at risk adds up

- Exact re-posts: $148.74 (2 extra charge(s))
- Near duplicates: $59.99 (1 extra charge(s))

## What was checked and NOT flagged

- TXN-3014: same customer (CUST-104) and amount ($59.99) as TXN-3004, but 5 hours later — a legitimate repeat purchase, outside the 10-minute window.
- TXN-3017: same amount ($59.99) as CUST-104's charges, but a different customer (CUST-115) — not a duplicate.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
