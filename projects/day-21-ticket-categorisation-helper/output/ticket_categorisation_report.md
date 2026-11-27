# Ticket Categorisation Report

Generated: 2026-11-27 09:20 · Tickets reviewed: 8

## 🔴 Actions needed — 6 item(s)

⚠️ **2 possible hidden P1(s)** — work these before the rest of the queue.

### 🔴 TKT-3101 — Checkout returns 500 for all customers

- Service: checkout-api · Currently: General / P3
- Suggestion: **Incident — Service Outage** → Application Support L2 · **P1** (confidence 75%, matched: all customers, nobody can)
- ▶ Re-categorise: 'General' → 'Incident — Service Outage', route to Application Support L2
- ▶ Raise priority: P3 → P1 ("all customers" — wide business impact; "nobody can" — wide business impact; "revenue" — wide business impact; 1200 affected users with failure signal '500')
- ▶ Possible hidden P1 — work this before the rest of the queue

### 🔴 TKT-3102 — Checkout 500 errors — payment timeout PAY-3002

- Service: checkout-api · Currently: Incident — Application Error / P2
- Suggestion: **Incident — Application Error** → Application Support L2 · **P1** (confidence 100%, matched: 500, error, failed, timeout)
- ▶ Raise priority: P2 → P1 (300 affected users with failure signal '500')
- ▶ Possible hidden P1 — work this before the rest of the queue

### 🟢 TKT-3103 — Password reset for new starter

- Service: identity · Currently: Access Request / P4
- Suggestion: **Access Request** → Service Desk · **P4** (confidence 100%, matched: password reset, new starter, access request, account)

### 🔴 TKT-3104 — Settlement file missing again

- Service: settlement-service · Currently: Incident — Application Error / P3
- Suggestion: **Batch & File Transfer** → Application Support L2 · **P2** (confidence 100%, matched: settlement file, batch, file missing, did not arrive, sftp)
- ▶ Re-categorise: 'Incident — Application Error' → 'Batch & File Transfer', route to Application Support L2
- ▶ Raise priority: P3 → P2 ("deadline today" — time-sensitive or blocking; "settlement" — time-sensitive or blocking; "blocking" — time-sensitive or blocking; 25 affected users)

### 🟢 TKT-3105 — Invoice export template not found error

- Service: billing-api · Currently: Incident — Application Error / P2
- Suggestion: **Incident — Application Error** → Application Support L2 · **P2** (confidence 100%, matched: 500, error, template not found)

### 🟢 TKT-3106 — How do I run the month-end report?

- Service: reporting · Currently: How-To / Knowledge / P4
- Suggestion: **How-To / Knowledge** → Service Desk · **P4** (confidence 100%, matched: how do i, training, guidance)

### 🔴 TKT-3107 — System slow

- Service: not stated · Currently: General / P3
- Suggestion: **human review** (confidence 0%, matched: nothing)
- ▶ Needs human review — too little detail to categorise (ask the reporter which service and what symptom)

### 🔴 TKT-3108 — Portal certificate expires Monday

- Service: customer-portal · Currently: Certificate & Security / P3
- Suggestion: **Certificate & Security** → Application Support L2 · **P2** (confidence 100%, matched: certificate, expires, tls, expiry)
- ▶ Raise priority: P3 → P2 ("expires monday" — time-sensitive or blocking; 500 affected users)

## Possible duplicates — merge or link, do not work twice

- **TKT-3101** ↔ **TKT-3102** — same service (checkout-api), shared subject words: 500, checkout

## Ranked action list

1. **TKT-3101** — Re-categorise: 'General' → 'Incident — Service Outage', route to Application Support L2
2. **TKT-3101** — Raise priority: P3 → P1 ("all customers" — wide business impact; "nobody can" — wide business impact; "revenue" — wide business impact; 1200 affected users with failure signal '500')
3. **TKT-3101** — Possible hidden P1 — work this before the rest of the queue
4. **TKT-3102** — Raise priority: P2 → P1 (300 affected users with failure signal '500')
5. **TKT-3102** — Possible hidden P1 — work this before the rest of the queue
6. **TKT-3104** — Re-categorise: 'Incident — Application Error' → 'Batch & File Transfer', route to Application Support L2
7. **TKT-3104** — Raise priority: P3 → P2 ("deadline today" — time-sensitive or blocking; "settlement" — time-sensitive or blocking; "blocking" — time-sensitive or blocking; 25 affected users)
8. **TKT-3108** — Raise priority: P3 → P2 ("expires monday" — time-sensitive or blocking; 500 affected users)
9. **TKT-3107** — Needs human review — too little detail to categorise (ask the reporter which service and what symptom)
10. **TKT-3101 / TKT-3102** — confirm the duplicate (same service (checkout-api), shared subject words: 500, checkout), link the reports, keep one master ticket

*Suggestions only — the analyst on triage confirms every change before it is applied to the ticket.*
