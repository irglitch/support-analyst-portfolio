# Incident SLA Report

**Source:** `incidents.csv`  
**Checked at:** 2026-11-11 09:20  
**Overall status:** 🔴 BREACH — action now  
**Open tickets:** 10 · **Breached:** 3 · **At risk:** 2 · **On track:** 5 · **Resolved/closed (excluded):** 1

## SLA targets (resolution)

| Priority | Target |
|---|---|
| P1 | 4h |
| P2 | 8h |
| P3 | 24h |
| P4 | 48h |

## All open tickets — sorted by deadline

| Ticket | Priority | Summary | Assignee | Created | Deadline | Time left | Status |
|---|---|---|---|---|---|---|---|
| INC-1042 | P1 | Checkout API returning 500s | Sam R | 2026-11-11 04:30 | 2026-11-11 08:30 | -50m | 🔴 In Progress |
| INC-1047 | P3 | Report export times out for large accounts | Ana M | 2026-11-10 09:00 | 2026-11-11 09:00 | -20m | 🔴 Open |
| INC-1050 | P1 | Settlement file rejected by bank | Sam R | 2026-11-11 05:15 | 2026-11-11 09:15 | -5m | 🔴 In Progress |
| INC-1043 | P2 | CRM sync stuck — new accounts not syncing | Priya K | 2026-11-11 02:00 | 2026-11-11 10:00 | 40m | 🟠 In Progress |
| INC-1044 | P3 | Invoice PDF download fails for some customers | Ana M | 2026-11-10 12:00 | 2026-11-11 12:00 | 2h 40m | 🟠 Open |
| INC-1046 | P1 | Mobile app login errors after update | Priya K | 2026-11-11 09:00 | 2026-11-11 13:00 | 3h 40m | 🟢 In Progress |
| INC-1049 | P2 | VPN drops for remote users | Priya K | 2026-11-11 07:30 | 2026-11-11 15:30 | 6h 10m | 🟢 In Progress |
| INC-1045 | P2 | Password reset email delayed | Sam R | 2026-11-11 08:00 | 2026-11-11 16:00 | 6h 40m | 🟢 Open |
| INC-1051 | P3 | Search returns stale results | Ana M | 2026-11-11 08:45 | 2026-11-12 08:45 | 23h 25m | 🟢 Open |
| INC-1048 | P4 | Dashboard chart labels misaligned | Sam R | 2026-11-10 14:00 | 2026-11-12 14:00 | 28h 40m | 🟢 Open |

## What to do now

**🔴 BREACHED — escalate immediately:**
- **INC-1042** (P1, Sam R): Checkout API returning 500s — breached 50m ago, deadline was 2026-11-11 08:30. Update the ticket, notify the duty manager, and record the breach reason.
- **INC-1047** (P3, Ana M): Report export times out for large accounts — breached 20m ago, deadline was 2026-11-11 09:00. Update the ticket, notify the duty manager, and record the breach reason.
- **INC-1050** (P1, Sam R): Settlement file rejected by bank — breached 5m ago, deadline was 2026-11-11 09:15. Update the ticket, notify the duty manager, and record the breach reason.

**🟠 AT RISK — act before the deadline:**
- **INC-1043** (P2, Priya K): CRM sync stuck — new accounts not syncing — only 40m left, deadline 2026-11-11 10:00. Chase the assignee and check whether the fix or a workaround can land in time.
- **INC-1044** (P3, Ana M): Invoice PDF download fails for some customers — only 2h 40m left, deadline 2026-11-11 12:00. Chase the assignee and check whether the fix or a workaround can land in time.

## Triage conclusion (auto-summary)

3 ticket(s) already breached — the oldest is **INC-1042** (P1, breached 50m ago). 2 more breach within hours — **INC-1043** first, in 40m. Start with the breaches: update, escalate, record the reason.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
