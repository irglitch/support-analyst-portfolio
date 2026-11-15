# Database Session Report

**Sessions in snapshot:** 14  
**Active:** 7 · **Blocked:** 4 · **Idle / idle-in-transaction:** 3  
**Longest-running session:** 2h 0m  
**Verdict:** 🔴 BLOCKING CHAIN — 2 blocker session(s) holding up 4 session(s); longest wait 10m 40s.

## 1. Blocking chains — who is holding everyone up

| Blocker | User / application | Running | Blocking | Longest waiter |
|---|---|---|---|---|
| SESS-101 | batch-user / overnight-settlement | 42m 0s | 3 session(s) | 10m 40s |
| SESS-102 | app-user / checkout-api | 18m 0s | 1 session(s) | 9m 0s |

What each blocker is running:

- **SESS-101** (`UPDATE transactions SET status='settled' WHERE batch_id=8814`)
- **SESS-102** (`UPDATE orders SET status='paid' WHERE order_id=55231`)

## 2. Blocked sessions — waiting on a lock

| Session | User / application | Waiting on | Wait event | Waiting |
|---|---|---|---|---|
| SESS-104 | app-user / checkout-api | SESS-101 | row lock on transactions | 10m 40s |
| SESS-105 | app-user / checkout-api | SESS-101 | row lock on transactions | 10m 10s |
| SESS-107 | app-user / billing-api | SESS-101 | row lock on transactions | 9m 50s |
| SESS-108 | app-user / checkout-api | SESS-102 | row lock on orders | 9m 0s |

What each blocked session is trying to run:

- **SESS-104** (`INSERT INTO payments (order_id, amount) VALUES (55231, 59.99)`)
- **SESS-105** (`UPDATE transactions SET status='paid' WHERE txn_id='TXN-3010'`)
- **SESS-107** (`SELECT balance FROM transactions WHERE customer_id='CUST-104' FOR UPDATE`)
- **SESS-108** (`UPDATE orders SET status='shipped' WHERE order_id=55231`)

## 3. Long-running active sessions (over 10 minutes)

| Session | User / application | Running |
|---|---|---|
| SESS-101 | batch-user / overnight-settlement | 42m 0s |
| SESS-103 | report-user / reporting | 12m 0s |

What each one is running:

- **SESS-101** (`UPDATE transactions SET status='settled' WHERE batch_id=8814`)
- **SESS-103** (`SELECT region, SUM(amount) FROM sales WHERE sale_date='2026-11-14' GROUP BY region`)

## 4. Idle-in-transaction sessions holding locks (over 5 minutes)

| Session | User / application | Idle in transaction for |
|---|---|---|
| SESS-102 | app-user / checkout-api | 18m 0s |

Last statement before going idle:

- **SESS-102** (`UPDATE orders SET status='paid' WHERE order_id=55231`)

## 5. Watch list — active sessions between 2 and 10 minutes

| Session | User / application | Running |
|---|---|---|
| SESS-112 | report-user / reporting | 6m 20s |
| SESS-114 | batch-user / overnight-settlement | 2m 10s |

## What was checked and NOT flagged

- SESS-110: idle for 2h 0m, but plain idle — not in a transaction, so it holds no locks. Harmless; do not kill it to 'free' anything.
- SESS-115: idle in transaction for 45s — under the 5-minute threshold. A short pause between statements, not a stuck session.
- SESS-109, SESS-111, SESS-113: normal fast queries (3s, 45s, 8s) — the app itself is not slow, the waits are.

This tool only reads the snapshot and reports — it never kills a session. Killing one is a DBA decision; see `RUNBOOK.md`.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
