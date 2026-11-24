# Root Cause Analysis — INC-2011: Checkout returning HTTP 500s

**Status:** FINAL | **Priority:** P1 | **Service:** checkout-api
**Detected:** 2026-11-23T09:02 | **Resolved:** 2026-11-23T10:47 | **Duration:** 1h 45m
**Author:** P. Kumar — Application Support | **Generated:** 2026-11-24 09:20

> Practice scenario with sample data, built for this portfolio — not employer work.

## 1. Executive summary

Between 09:02 and 10:47 on Monday 2026-11-23, checkout-api returned HTTP 500 to most checkout attempts. The cause was database connection-pool exhaustion: an overnight configuration change (CHG-8841) lowered the pool from 200 to 50 connections while Monday-morning checkout traffic stayed at its usual peak, so new checkouts queued, timed out after 30 seconds, and failed. Service was restored by raising the pool back to 200 and restarting checkout-api; the backlog cleared by 10:47 with no double-charges found.

## 2. Impact

- **Users affected:** approx. 1,850 customers attempting checkout
- **Failed transactions:** 1,240 failed checkout attempts (HTTP 500)
- **Business impact:** Estimated $38,450 of checkout value interrupted during the 105-minute outage; no orders were double-charged (verified against the Day 08 duplicate detector). Checkout was unavailable for most of the morning peak.
- **Detection:** Service health check (Day 13 probe) alerted at 09:02; first customer report at 09:11

## 3. Timeline (all times America/Toronto)

| Time | Elapsed | Event |
|---|---|---|
| 2026-11-23T02:15 | — | CHG-8841 applied: checkout-api connection pool lowered 200 → 50 |
| 2026-11-23T09:02 | 0m | Health-check probe alerts: checkout-api latency over threshold, first HTTP 500s seen |
| 2026-11-23T09:11 | 9m | First customer report — checkout failing at payment step |
| 2026-11-23T09:20 | 18m | P1 declared; INC-2011 opened; duty manager and platform team paged |
| 2026-11-23T09:35 | 33m | Log triage (Day 01 method): 500s cluster on checkout-api, DB timeout errors dominate |
| 2026-11-23T09:58 | 56m | Pool exhaustion confirmed; CHG-8841 identified as the change in the window |
| 2026-11-23T10:12 | 1h 10m | Pool raised back to 200; checkout-api restarted |
| 2026-11-23T10:31 | 1h 29m | Error rate back under 1%; checkout succeeding; backlog draining |
| 2026-11-23T10:47 | 1h 45m | Backlog cleared; duplicate check run — no double-charges; INC-2011 resolved |

## 4. Root cause

Connection-pool exhaustion on checkout-api. CHG-8841 (applied 02:15, Sunday night) reduced the database connection pool from 200 to 50 as part of a cost-saving change, with no load test against Monday-morning peak traffic. At 09:02 the pool saturated, checkout requests queued behind the 30-second timeout, and the service returned HTTP 500. The pool setting was not covered by the change's rollback criteria, so the change stayed live until support identified it at 09:58.

## 5. Five whys

1. **Why?** Checkout returned HTTP 500 because checkout-api could not get a database connection in time.
2. **Why?** It could not get a connection because the connection pool was exhausted — all 50 connections were in use.
3. **Why?** The pool was exhausted because CHG-8841 had lowered it from 200 to 50 overnight.
4. **Why?** The change lowered it because the change request assumed off-peak traffic levels and was never tested against Monday-morning peak load.
5. **Why?** It was never tested because the change process has no mandatory load check for configuration changes that touch connection limits.

## 6. What went well / what went badly

**Went well:**
- Detection was fast — the health-check probe alerted at 09:02, nine minutes before the first customer report.
- Log triage narrowed the fault to checkout-api and DB timeouts within 15 minutes.
- The duplicate-transaction check ran before closure, so the business could be told confidently that nobody was charged twice.

**Went badly:**
- CHG-8841 went live with no load test against peak traffic and no rollback trigger on the pool setting.
- The P1 breached its 60-minute SLA — resolution took 105 minutes, 45 minutes over target.
- No runbook existed for pool exhaustion, so the team spent 23 minutes (09:35–09:58) confirming what a checklist would have shown in five.

## 7. Action items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
| 1 | Add a mandatory load/peak-traffic check to the change process for any configuration change touching connection limits | Change Manager | 2026-12-04 | Open |
| 2 | Add a connection-pool usage alert at 80% so exhaustion is caught before timeouts start | Platform Team | 2026-11-27 | Open |
| 3 | Write a pool-exhaustion runbook (symptoms, checks, safe pool raise, restart steps) | P. Kumar — Application Support | 2026-11-26 | In progress |
| 4 | Review CHG-8841 approval — why the rollback criteria did not cover the pool setting | Duty Manager | 2026-11-28 | Open |

## 8. Evidence

- Health-check probe log 2026-11-23 09:02–10:47 (Day 13 checker output)
- checkout-api error log extract: DB timeout errors dominate from 09:02 (Day 01 log triage)
- CHG-8841 change record — pool 200 → 50 applied 02:15
- Duplicate-transaction check output 10:47 — 0 double-charges (Day 08 detector)

## 9. Follow-up

Present at the business review on 2026-11-25. Re-check action items weekly until all four are closed; if the pool alert (due 2026-11-27) slips, escalate to the duty manager. If checkout 500s recur before the alert is live, treat it as a repeat incident and link it to this RCA.
