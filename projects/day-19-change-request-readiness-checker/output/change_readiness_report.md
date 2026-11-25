# Change Request Readiness Report

**Review:** CAB 2026-11-26 — changes scheduled for the Thursday evening window | **Generated:** 2026-11-25 09:20 (America/Toronto)

## 🔴 NOT READY — 2 of 5 changes blocked (3 blockers, 3 warnings)

Do not approve the blocked changes at CAB until their blockers are cleared. The ready changes can proceed on their own windows.

**Summary:** 2 ready · 1 ready with conditions · 2 not ready · 5 changes checked

| Change | Service | Risk | Window | Verdict | Blockers | Warnings |
|---|---|---|---|---|---|---|
| CHG-8901 — Payment gateway connection pool 50 -> 120 (INC-2011 follow-up) | payment-api | high | 2026-11-26 22:00 → 2026-11-26 23:30 (90m) | 🟢 READY | 0 | 0 |
| CHG-8902 — Settlement service v2.4 deploy | settlement-service | medium | 2026-11-26 22:00 → 2026-11-26 23:00 (60m) | 🔴 NOT READY | 2 | 0 |
| CHG-8903 — CRM sync retry patch | crm-sync | medium | 2026-11-26 23:00 → 2026-11-27 00:00 (60m) | 🟡 READY WITH CONDITIONS | 0 | 2 |
| CHG-8904 — Reporting database index on transactions | reporting-db | medium | 2026-11-26 22:30 → 2026-11-26 23:30 (60m) | 🔴 NOT READY | 1 | 1 |
| CHG-8905 — Notification service TLS certificate renewal | notification-service | low | 2026-11-26 22:00 → 2026-11-26 22:30 (30m) | 🟢 READY | 0 | 0 |

## Actions for CAB (blockers first)

- 🔴 **CHG-8902** — No rollback trigger — nobody has defined when to back out
- 🔴 **CHG-8902** — Approval still outstanding: service-owner-settlements (service owner)
- 🔴 **CHG-8904** — Window too short to roll back: implementation 50m + rollback 20m = 70m in a 60m window
- 🟡 **CHG-8903** — Stakeholders not yet notified (no outage expected)
- 🟡 **CHG-8903** — No peer review recorded for a medium/high-risk change
- 🟡 **CHG-8904** — Dependencies not checked

## Change detail

### 🟢 CHG-8901 — Payment gateway connection pool 50 -> 120 (INC-2011 follow-up) — READY

- **Service:** payment-api · **Risk:** high · **Type:** normal · **Implementer:** platform-team
- **Window:** 2026-11-26 22:00 → 2026-11-26 23:30 (90m) · **Estimated implementation:** 30m
- **Checks passed:**
  - ✅ Description explains what is changing and why
  - ✅ Risk assessed: high
  - ✅ Impact names affected services: payment-api, checkout-api
  - ✅ Tested in staging: pass
  - ✅ Load test evidence present (required for high-risk / limit changes)
  - ✅ Rollback plan documented
  - ✅ Rollback trigger defined
  - ✅ Window fits implementation + rollback (40m of 90m)
  - ✅ All recorded approvals are approved
  - ✅ CAB approval recorded (required for high risk)
  - ✅ Stakeholders notified
  - ✅ Dependencies checked
  - ✅ Peer reviewed
  - ✅ Post-implementation verification defined (3 steps)

### 🔴 CHG-8902 — Settlement service v2.4 deploy — NOT READY

- **Service:** settlement-service · **Risk:** medium · **Type:** normal · **Implementer:** settlements-team
- **Window:** 2026-11-26 22:00 → 2026-11-26 23:00 (60m) · **Estimated implementation:** 25m
- **Blockers:**
  - 🔴 No rollback trigger — nobody has defined when to back out
  - 🔴 Approval still outstanding: service-owner-settlements (service owner)
- **Checks passed:**
  - ✅ Description explains what is changing and why
  - ✅ Risk assessed: medium
  - ✅ Impact names affected services: settlement-service
  - ✅ Tested in staging: pass
  - ✅ Rollback plan documented
  - ✅ Window fits implementation + rollback (40m of 60m)
  - ✅ Stakeholders notified
  - ✅ Dependencies checked
  - ✅ Peer reviewed
  - ✅ Post-implementation verification defined (2 steps)

### 🟡 CHG-8903 — CRM sync retry patch — READY WITH CONDITIONS

- **Service:** crm-sync · **Risk:** medium · **Type:** normal · **Implementer:** crm-team
- **Window:** 2026-11-26 23:00 → 2026-11-27 00:00 (60m) · **Estimated implementation:** 20m
- **Warnings:**
  - 🟡 Stakeholders not yet notified (no outage expected)
  - 🟡 No peer review recorded for a medium/high-risk change
- **Checks passed:**
  - ✅ Description explains what is changing and why
  - ✅ Risk assessed: medium
  - ✅ Impact names affected services: crm-sync
  - ✅ Tested in staging: pass
  - ✅ Rollback plan documented
  - ✅ Rollback trigger defined
  - ✅ Window fits implementation + rollback (30m of 60m)
  - ✅ All recorded approvals are approved
  - ✅ Dependencies checked
  - ✅ Post-implementation verification defined (2 steps)

### 🔴 CHG-8904 — Reporting database index on transactions — NOT READY

- **Service:** reporting-db · **Risk:** medium · **Type:** normal · **Implementer:** data-team
- **Window:** 2026-11-26 22:30 → 2026-11-26 23:30 (60m) · **Estimated implementation:** 50m
- **Blockers:**
  - 🔴 Window too short to roll back: implementation 50m + rollback 20m = 70m in a 60m window
- **Warnings:**
  - 🟡 Dependencies not checked
- **Checks passed:**
  - ✅ Description explains what is changing and why
  - ✅ Risk assessed: medium
  - ✅ Impact names affected services: reporting-db
  - ✅ Tested in staging: pass
  - ✅ Rollback plan documented
  - ✅ Rollback trigger defined
  - ✅ All recorded approvals are approved
  - ✅ Stakeholders notified
  - ✅ Peer reviewed
  - ✅ Post-implementation verification defined (2 steps)

### 🟢 CHG-8905 — Notification service TLS certificate renewal — READY

- **Service:** notification-service · **Risk:** low · **Type:** standard · **Implementer:** platform-team
- **Window:** 2026-11-26 22:00 → 2026-11-26 22:30 (30m) · **Estimated implementation:** 10m
- **Checks passed:**
  - ✅ Description explains what is changing and why
  - ✅ Risk assessed: low
  - ✅ Impact names affected services: notification-service
  - ✅ Tested in staging: pass
  - ✅ Rollback plan documented
  - ✅ Rollback trigger defined
  - ✅ Window fits implementation + rollback (15m of 30m)
  - ✅ All recorded approvals are approved
  - ✅ Stakeholders notified
  - ✅ Dependencies checked
  - ✅ Peer reviewed
  - ✅ Post-implementation verification defined (2 steps)

---

*Practice scenario with sample data, built for this portfolio — not employer work. This report supports the CAB decision; it does not approve or implement any change.*
