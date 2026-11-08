# Incident Triage Report

**Source log:** `app.log`  
**Lines parsed:** 25 · **Unparsed lines:** 0  
**Errors (ERROR+FATAL):** 13  
**Suggested priority:** P1 (candidate) — Dependency-failure error present: DB_CONN_TIMEOUT  
**Most affected service:** `payment-api`

## Counts by level

| Level | Count |
|---|---|
| ERROR | 13 |
| WARN | 5 |
| INFO | 7 |

## Errors by service

| Service | Errors |
|---|---|
| payment-api | 10 |
| file-transfer | 2 |
| reconciliation | 1 |

## Errors by code (first → last seen)

| Error code | Count | First seen | Last seen |
|---|---|---|---|
| DB_CONN_TIMEOUT | 10 | 2026-11-07T08:12:04Z | 2026-11-07T08:28:59Z |
| FILE_NOT_FOUND | 2 | 2026-11-07T08:21:30Z | 2026-11-07T08:22:04Z |
| VALIDATION | 1 | 2026-11-07T08:34:02Z | 2026-11-07T08:34:02Z |

## Triage conclusion (auto-summary)

The dominant failure is **DB_CONN_TIMEOUT** (10 occurrences, 2026-11-07T08:12:04Z → 2026-11-07T08:28:59Z) on **payment-api**. Start the investigation there, not with the user-facing symptom.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
