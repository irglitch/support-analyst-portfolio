# Daily BAU Health-Check Report

**As of:** 2026-11-23 09:20 · **Overall: 🔴 RED**

## Summary

| Area | Status | Headline |
|---|---|---|
| Services | 🔴 CRITICAL | 1 down, 1 degraded of 6 |
| Disk space | 🔴 CRITICAL | 1 FAIL, 1 WARN of 3 mounts |
| Incident SLA | 🔴 CRITICAL | 1 breached, 1 at risk of 5 open tickets |
| Files | 🔴 CRITICAL | 1 missing, 1 late of 4 expected |
| Certificates | 🔴 CRITICAL | 1 critical, 2 warning of 4 |

## Top actions — work these in order

1. Page the platform team: **notification-service** is DOWN since 2026-11-23 09:02 (3 failed probe(s) — Connection refused). Check the service, then its dependency.
2. Chase the sender (partner-bank): **settlement-20261123.csv** never arrived (due 2026-11-23 07:00) — the downstream batch cannot start without it.
3. Renew **Payment Gateway API** certificate (api.payment-gateway.example.com) — it expires today. Owner: platform-team.
4. Escalate **INC-2011** (P1, Checkout 500 errors) to the duty manager — BREACHED 35m over SLA. Owner: duty-manager.
5. Clear space on **/data** (91% used) — fills around 15:45 (6.4h at +1.4%/h). Start with the largest directories (see Day 14) and the log rotation job (see Day 16).
6. Investigate **settlement-service**: DEGRADED — 1180 ms vs 800 ms threshold. Slow, not down — check the dependency before it becomes an outage.
7. Confirm **fx-rates-20261123.csv** (Late) with fx-vendor — check it is complete before the batch consumes it.
8. Raise a renewal ticket for **SSO** (sso.example.com) — expires in 19 day(s). Owner: identity-team.
9. Raise a renewal ticket for **Customer Portal** (portal.example.com) — expires in 24 day(s). Owner: web-team.
10. Chase **INC-2014** (P2, CRM sync stale data) — AT RISK — breaches in 30m. Owner: platform-team.
11. Plan space on **/var** (84% used) — fills around 2026-11-24 05:20.

## Services

| Service | Status | Latency | Uptime vs SLA | Failed probes | Last error |
|---|---|---|---|---|---|
| payment-api | 🟢 UP | 214 ms / 500 ms | 99.98% vs 99.9% | 0 | — |
| crm-sync | 🟢 UP | 388 ms / 800 ms | 99.62% vs 99.5% | 0 | — |
| settlement-service | 🟡 DEGRADED | 1180 ms / 800 ms | 100.00% vs 99.9% | 0 | — |
| sftp-gateway | 🟢 UP | 96 ms / 500 ms | 99.99% vs 99.9% | 0 | — |
| reporting-service | 🟢 UP | 640 ms / 1000 ms | 99.87% vs 99.5% | 0 | — |
| notification-service | 🔴 DOWN | — | 99.41% vs 99.5% | 3 | Connection refused |

## Disk space

| Mount | Used | Inodes | Growth | Fills in | Status |
|---|---|---|---|---|---|
| /data | 91% of 500G | 90% | +1.4%/h | 6.4h | 🔴 CRITICAL |
| /var | 84% of 600G | 71% | +0.8%/h | 20.0h | 🟡 WARNING |
| / | 62% of 100G | 55% | +0.1%/h | 380.0h | 🟢 OK |

## Incident SLA (open tickets)

| Ticket | Priority | Summary | Status | Owner |
|---|---|---|---|---|
| INC-2011 | P1 | Checkout 500 errors | 🔴 BREACHED 35m over SLA | duty-manager |
| INC-2014 | P2 | CRM sync stale data | 🟡 AT RISK — breaches in 30m | platform-team |
| INC-2015 | P3 | Report export slow | 🟢 ON TRACK — 22h 40m left | support-team |
| INC-2016 | P2 | Settlement file late | 🟢 ON TRACK — 4h 55m left | ops-team |
| INC-2017 | P4 | Dashboard typo | 🟢 ON TRACK — 47h 10m left | support-team |

## Files expected this morning

| File | Due | Arrived | Status |
|---|---|---|---|
| settlement-20261123.csv | 2026-11-23 07:00 | — | 🔴 never arrived |
| fx-rates-20261123.csv | 2026-11-23 07:00 | 2026-11-23 07:25 | 🟡 Late |
| audit-log-20261123.csv | 2026-11-23 07:00 | 2026-11-23 06:58 | 🟢 arrived on time |
| promo-codes-20261123.csv | 2026-11-23 07:00 | 2026-11-23 06:41 | 🟢 arrived on time |

## Certificates

| Hostname | Service | Expires | Status | Owner |
|---|---|---|---|---|
| api.payment-gateway.example.com | Payment Gateway API | 2026-11-23 (expires in 0 day(s)) | 🔴 CRITICAL | platform-team |
| sso.example.com | SSO | 2026-12-12 (expires in 19 day(s)) | 🟡 WARNING | identity-team |
| portal.example.com | Customer Portal | 2026-12-17 (expires in 24 day(s)) | 🟡 WARNING | web-team |
| ca.internal.example.com | Internal CA | 2027-06-01 (expires in 190 day(s)) | 🟢 OK | platform-team |

## What to do next

- RED: page the duty manager with this report attached and work the action list in order — the top item is the one that hurts the business first.
- AMBER: raise tickets for the warnings and re-run the check after the 10:00 batch — a warning left alone becomes tomorrow's RED.
- GREEN: file the report; the check still ran, and the record proves the morning was clean.
- Detail for each area lives in the earlier projects: services (Day 13), disks (Day 14), SLA (Day 05), files (Day 04), certificates (Day 15), log cleanup (Day 16).

*Practice scenario with sample data, built for this portfolio — not employer work.*
