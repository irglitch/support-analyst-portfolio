# Error Code Knowledge Base — Search Report

**Knowledge base:** `knowledge_base.json`  
**Search:** `timeout`  
**Matches:** 3

Entries are ranked: exact error-code match first, then code substring, then keyword in the symptom / cause / fix. Within each rank, the fix seen most often comes first.

## Matches

### PAY-3002 — Card authorisation fails with a gateway timeout

- **System:** Payments · **Severity:** P1 · **Seen:** 6 time(s) · **Last fixed:** 2026-10-22 (INC-1048)
- **Cause:** Payment gateway vendor latency spike — the vendor's own status page showed degraded service.
- **Fix that worked:** Check the vendor status page first. Retry failed authorisations with back-off; queue any that still fail and re-run them once the vendor reports recovered. Do not re-charge the customer twice.
- **Match:** keyword in the symptom

### DB-1045 — Checkout fails: database connection timeout after 30s

- **System:** Database · **Severity:** P1 · **Seen:** 5 time(s) · **Last fixed:** 2026-10-20 (INC-1042)
- **Cause:** Connection pool exhausted — the overnight batch held connections open and never released them.
- **Fix that worked:** Check active sessions, kill the idle batch sessions, then restart the connection pool. Do NOT restart the app first — the pool will exhaust again within minutes.
- **Match:** keyword in the symptom

### RPT-207 — Monthly report fails with a timeout after 10 minutes

- **System:** Reporting · **Severity:** P3 · **Seen:** 3 time(s) · **Last fixed:** 2026-10-07 (INC-1015)
- **Cause:** Report query scans the full history table because no date filter was applied.
- **Fix that worked:** Add a date filter for the reporting month, re-run the report, and schedule it off-peak so it does not compete with the morning batch.
- **Match:** keyword in the symptom

## What to do with the top match

1. Try the fix for **PAY-3002** first — it worked 6 time(s) before.
2. If the fix works, note the ticket number in your ticket so the next analyst can trace it back.
3. If the fix does NOT work, do not keep retrying it — the symptom may look the same but the cause may be new. Escalate with the evidence and add a new entry once the real cause is found.

Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.
