# Runbook — Log Triage (Day 01)

## 1. Verify before you escalate (5 minutes)
- Re-run the analyzer on the **last 30 minutes** of live log — is the top error still growing?
- Check one affected transaction in the application UI — is it really stuck in Pending?
- Confirm the suggested service with one independent check (DB status page / infra chat).

## 2. Escalate with facts, not feelings
Paste into the incident ticket:
- **Start time:** first-seen timestamp of the dominant error code
- **Impact:** most affected service + error count + user symptom
- **Pattern:** one code repeating = likely one cause; many codes = check wider
- **Priority suggestion** from the report, with the reason line

Escalation path for a `DB_CONN_TIMEOUT` pattern: Database / Infrastructure team first,
application team copied — the app is the victim here, not the cause.

## 3. Communicate
- Update the ticket every 30 minutes during a P1/P2, even if the update is "no change".
- Tell users the workaround if one exists (hold submissions, retry after recovery) —
  never tell users to "keep retrying" during a connection outage; it makes the queue worse.

## 4. After recovery
- Re-run the analyzer — error count should fall to zero; note the recovery timestamp.
- Count and list transactions held in Pending during the window for the business to validate.
- Check knock-on effects separately (here: the missing settlement file needs a re-send,
  it does not fix itself when the database recovers).

## 5. RCA prompts
- What changed before 08:12? (deploy, patch, connection-pool setting, DB maintenance?)
- Why did monitoring not alert before users called? Add an alert on the dominant error code.
- Problem record: link repeat occurrences — one timeout is an incident, ten is a problem.
