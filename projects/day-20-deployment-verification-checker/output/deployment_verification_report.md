# Deployment Verification Report

**Window:** Wednesday 2026-11-25 evening window (22:00-23:30) — verified Thursday 2026-11-26 09:20 | **Generated:** 2026-11-26 09:20 (America/Toronto)

## 🔴 FAILED — 3 of 6 deployments not verified (4 failures, 1 warning)

Do not close the failed change tickets. The verified changes can close; the failures below need a fix or a rollback first.

**Summary:** 2 verified · 1 verified with warnings · 3 failed · 6 deployments checked

| Change | Service | Expected | Observed | Verdict | Failures | Warnings |
|---|---|---|---|---|---|---|
| CHG-8851 — Checkout API v3.2.1 — session timeout fix | checkout-api | v3.2.1 | completed | 🟡 VERIFIED WITH WARNINGS | 0 | 1 |
| CHG-8852 — Settlement service v2.3.1 — rejected-file retry limit 3 to 5 | settlement-service | v2.3.1 | completed | 🟢 VERIFIED | 0 | 0 |
| CHG-8853 — Search API v5.0 — ranking update | search-api | v5.0.0 | completed | 🔴 FAILED | 1 | 0 |
| CHG-8854 — Billing API — enable invoice-export feature flag | billing-api | v2.8.0 | completed | 🔴 FAILED | 2 | 0 |
| CHG-8855 — Customer portal TLS certificate renewal | customer-portal | deployed | completed | 🔴 FAILED | 1 | 0 |
| CHG-8856 — Reporting database index — deferred by CAB to next week | reporting-db | held | not_deployed | 🟢 VERIFIED | 0 | 0 |

## Actions (failures first)

- 🔴 **CHG-8853** — Partial deployment — expected v5.0.0 everywhere, still on the old build: search-03 (v4.7.2)
- 🔴 **CHG-8854** — Smoke test FAILED (export a test invoice): test invoice export returned HTTP 500 (template not found)
- 🔴 **CHG-8854** — Error rate 6.4% breached the rollback trigger (5.0%) — roll back per the change plan
- 🔴 **CHG-8855** — Live endpoint still serves the old certificate (expires 2026-12-10, expected on/after 2027-01-01) — the renewal is not live
- 🟡 **CHG-8851** — Completed 11m after the window closed (2026-11-25T23:30) — record the overrun on the ticket

## Deployment detail

### 🟡 CHG-8851 — Checkout API v3.2.1 — session timeout fix — VERIFIED WITH WARNINGS

- **Service:** checkout-api · **Expected outcome:** deployed · **Observed status:** completed
- **Completed:** 2026-11-25 23:41 · **Window ended:** 2026-11-25 23:30
- **Warnings:**
  - 🟡 Completed 11m after the window closed (2026-11-25T23:30) — record the overrun on the ticket
- **Checks passed:**
  - ✅ Deployment completed
  - ✅ All 3 expected instances reporting
  - ✅ Version v3.2.1 live on all 3 instance(s)
  - ✅ Health endpoint OK
  - ✅ Smoke test passed (test checkout end to end)
  - ✅ Error rate 0.4% within limits

### 🟢 CHG-8852 — Settlement service v2.3.1 — rejected-file retry limit 3 to 5 — VERIFIED

- **Service:** settlement-service · **Expected outcome:** deployed · **Observed status:** completed
- **Completed:** 2026-11-25 22:48 · **Window ended:** 2026-11-25 23:30
- **Checks passed:**
  - ✅ Deployment completed
  - ✅ All 2 expected instances reporting
  - ✅ Version v2.3.1 live on all 2 instance(s)
  - ✅ Config retry_limit = 5 on every instance
  - ✅ Health endpoint OK
  - ✅ Smoke test passed (process the test settlement file)
  - ✅ Error rate 0.2% within limits
  - ✅ Completed inside the scheduled window

### 🔴 CHG-8853 — Search API v5.0 — ranking update — FAILED

- **Service:** search-api · **Expected outcome:** deployed · **Observed status:** completed
- **Completed:** 2026-11-25 23:05 · **Window ended:** 2026-11-25 23:30
- **Failures:**
  - 🔴 Partial deployment — expected v5.0.0 everywhere, still on the old build: search-03 (v4.7.2)
- **Checks passed:**
  - ✅ Deployment completed
  - ✅ All 3 expected instances reporting
  - ✅ Health endpoint OK
  - ✅ Smoke test passed (run the standard search query set)
  - ✅ Error rate 1.1% within limits
  - ✅ Completed inside the scheduled window

### 🔴 CHG-8854 — Billing API — enable invoice-export feature flag — FAILED

- **Service:** billing-api · **Expected outcome:** deployed · **Observed status:** completed
- **Completed:** 2026-11-25 22:57 · **Window ended:** 2026-11-25 23:30
- **Failures:**
  - 🔴 Smoke test FAILED (export a test invoice): test invoice export returned HTTP 500 (template not found)
  - 🔴 Error rate 6.4% breached the rollback trigger (5.0%) — roll back per the change plan
- **Checks passed:**
  - ✅ Deployment completed
  - ✅ All 2 expected instances reporting
  - ✅ Version v2.8.0 live on all 2 instance(s)
  - ✅ Config invoice_export_enabled = True on every instance
  - ✅ Health endpoint OK
  - ✅ Completed inside the scheduled window

### 🔴 CHG-8855 — Customer portal TLS certificate renewal — FAILED

- **Service:** customer-portal · **Expected outcome:** deployed · **Observed status:** completed
- **Completed:** 2026-11-25 22:35 · **Window ended:** 2026-11-25 23:30
- **Failures:**
  - 🔴 Live endpoint still serves the old certificate (expires 2026-12-10, expected on/after 2027-01-01) — the renewal is not live
- **Checks passed:**
  - ✅ Deployment completed
  - ✅ All 2 expected instances reporting
  - ✅ Health endpoint OK
  - ✅ Smoke test passed (load the portal login page over HTTPS)
  - ✅ Error rate 0.1% within limits
  - ✅ Completed inside the scheduled window

### 🟢 CHG-8856 — Reporting database index — deferred by CAB to next week — VERIFIED

- **Service:** reporting-db · **Expected outcome:** held · **Observed status:** not_deployed
- **Checks passed:**
  - ✅ Correctly not deployed — the CAB deferral held
  - ✅ Version unchanged at schema-114 on all 1 instance(s)
  - ✅ Health endpoint OK

---

*Practice scenario with sample data, built for this portfolio — not employer work. This report verifies deployments; it does not deploy, restart, or roll back anything.*
