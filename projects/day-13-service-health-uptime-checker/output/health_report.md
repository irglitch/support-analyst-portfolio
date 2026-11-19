# Service Health / Uptime Report

**As of:** 2026-11-19 09:20 · **Window:** last 24 hours (probes every 5 minutes)

## Verdict: 🔴 CRITICAL

A critical service is down.

## Services

| Service | Status | Uptime | SLA | Avg latency | p95 | Last probe |
|---|---|---|---|---|---|---|
| payment-api (critical) | 🟢 UP | 99.65% | 99.5% | 198 ms | 272 ms | 09:20 |
| customer-portal (critical) | 🟢 UP | 100.00% | 99.5% | 144 ms | 195 ms | 09:20 |
| settlement-service (critical) | 🟡 DEGRADED | 100.00% | 99.5% | 1279 ms | 1567 ms | 09:20 |
| crm-sync (critical) | 🔴 DOWN | 97.92% | 99.5% | 234 ms | 310 ms | 09:20 |
| file-gateway | 🟢 UP | 99.65% | 99.0% | 346 ms | 467 ms | 09:20 |
| notification-service | 🟢 UP | 100.00% | 99.0% | 101 ms | 136 ms | 09:20 |

## What needs attention

### 🟡 settlement-service — DEGRADED

- Average latency 1279 ms exceeds 800 ms threshold.
- 0 failed of 288 probes in the window; latency threshold 800 ms, SLA 99.5%.

### 🔴 crm-sync — DOWN

- Failing now — 6 consecutive failed probes since 08:55.
- Uptime 97.92% is below SLA 99.5%.
- Outage started 2026-11-19 08:55 (25 minutes ago); last error: "Connection refused".
- 6 failed of 288 probes in the window; latency threshold 500 ms, SLA 99.5%.

## Actions

- Raise settlement-service with the service owner — Average latency 1279 ms exceeds 800 ms threshold.
- Escalate crm-sync to the platform team now — down since 08:55 (25 min), 6 consecutive failed probes, last error "Connection refused".
- Re-run this check after any fix and keep both reports — the before/after is the incident record.

_Practice scenario with sample data, built for this portfolio — not employer work._
