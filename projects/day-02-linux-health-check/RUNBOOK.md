# Runbook — Linux Health Check (Day 02)

## 1. Verify before you escalate (5 minutes)
- Re-run the script live on the affected host — a snapshot is evidence, the live
  run is the current truth. Has anything changed since the snapshot was taken?
- Confirm the symptom yourself: open the application and time one slow page.
  "Slow for everyone" and "slow for one user" are different incidents.
- Check the top process by name: is it the application itself, or something else
  (a backup, a runaway job) stealing CPU?

## 2. Escalate with facts, not feelings
Attach the report to the incident ticket and quote the FAIL lines:
- **Disk:** root at 92% — find what's filling it (`du -sh /var/log/*`) before it hits 100% and stops writes entirely
- **Service:** `payment-api` is failed — check its own log for the stop reason before restarting it; a restart without the reason just buys time
- **Load:** 2.10 per core — the box is oversubscribed, not just busy

Escalation path: Infrastructure / Linux admin team for disk and service recovery;
application team copied — the app is a victim of the full disk and the stopped
service until proven otherwise.

## 3. Communicate
- Tell users what is happening in plain language: "the server's main disk is
  almost full and one service has stopped — we're clearing space and restarting it."
- Update the ticket every 30 minutes during a P1/P2, even if the update is "no change".
- Never promise a time you don't control ("back in 10 minutes") — promise the
  next update instead.

## 4. After recovery
- Re-run the script — every check should be PASS, and the exit code 0. Note the recovery timestamp.
- Re-check the disk a day later: if it filled up once, it will fill up again without log rotation or a cleanup job (see Day 16).
- Confirm `payment-api` stays up for at least an hour — a service that stops again was never really fixed.

## 5. RCA prompts
- What filled the disk? (Logs with no rotation? A stuck batch writing errors? A backup landing in the wrong place?)
- Why did the service stop — and why did nobody notice until users called? Add a disk-space alert at 80% and a service-down alert.
- Why was memory at 88% with swap in use — is the server sized right for the load, or is something leaking?
- Problem record: if the disk fills every few weeks, this is a problem to fix, not an incident to repeat.
