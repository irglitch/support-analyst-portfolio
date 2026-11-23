# Runbook — Daily BAU Health-Check Report (Day 17)

## 1. Verify before you escalate (5–10 minutes)
- Re-run the check live — `./run_bau_check.sh --live` — a snapshot
  is evidence, the live run is the current truth. Anything that
  changed since 09:20 (a service recovered, a file arrived late)
  changes the action list.
- Spot-check the top item yourself before paging anyone:
  `curl https://notify.example.com/health` for the down service,
  `ls -l` in the drop folder for the missing settlement file,
  `df -h /data` for the disk. The report should match what the
  system says — if it doesn't, the snapshot is stale and the report
  is wrong, not the system.
- Check whether the down service and the missing file are the same
  incident: if the notification service is what tells the partner
  bank the file is expected, one fix may clear two reds. Don't
  escalate them as two unrelated outages until you've checked.
- Confirm the certificate expiry independently — `openssl s_client`
  against the gateway, or the Day 15 checker — before telling the
  business payments will break today.

## 2. Escalate with facts, not feelings
Attach the report to the incident ticket and quote the action lines:
- **What:** 🔴 RED at 09:20 — 1 service down, 1 degraded, 1 file
  missing, 1 P1 breached, 1 disk at 91%, 1 certificate expiring today
- **First:** notification-service DOWN since 09:02, 3 failed probes,
  "Connection refused" — platform team owns it
- **Business impact:** the settlement batch cannot start without
  settlement-20261123.csv, and the Payment Gateway certificate
  lapsing today would break payments, not just notifications
- **Deadline:** INC-2014 breaches in 30 minutes; /data fills around
  15:45; the gateway certificate expires at end of day
- **What is fine:** crm-sync recovered, payment-api healthy, 3 of 5
  open tickets on track — say so, so nobody re-investigates the
  healthy areas

Escalation path: duty manager first (a RED morning is their call),
then platform team (down service + gateway certificate), partner
bank (missing file), identity team (SSO certificate). **Do not
restart the down service yourself** unless the runbook for that
service allows it — a restart without knowing why it stopped hides
the cause and can lose queued notifications.

## 3. Communicate
- Tell users and the duty manager what is happening in plain language:
  "the morning check is red — one notification service is down, the
  settlement file hasn't arrived, and a payment certificate expires
  today. We're working the service and the file first; payments are
  still working while the certificate is renewed."
- Give the next update time, not just the problem: "next update at
  10:00, or sooner if the service recovers or the file arrives."
- Update the ticket as each action clears — a RED report with items
  ticked off is the record that the morning was handled, and it's
  what the next shift reads.

## 4. After recovery
- Re-run the tool — it should report AMBER, then GREEN, as items
  clear. Note the recovery time of each item in the ticket.
- Confirm the settlement batch ran cleanly once the file arrived —
  a batch that started late may need a re-run check (see Day 12),
  and the FX rates file that arrived 25 minutes late should be
  checked for completeness before the batch consumes it.
- Confirm the gateway certificate renewal actually took effect —
  check the live certificate, not just the ticket saying it was
  renewed (see Day 15).
- Schedule the check: run it every morning at 09:20 and page on
  exit code 2. A RED that nobody sees until 11:00 is the same
  incident, two hours older.

## 5. RCA prompts
- Why did five areas go red on the same morning — is there a common
  cause (a bad overnight change, a partner outage), or is this five
  separate problems that all happened to land on Monday?
- Why was the gateway certificate still unrenewed on its expiry day
  when Day 15 flagged it on Saturday — did the renewal ticket get
  raised, and who owned it?
- Why did the settlement file go missing without an alert at 07:00 —
  the Day 04 monitor should have caught it two hours before this
  report did.
- Is the 09:20 check early enough — should the file and certificate
  checks run at 07:00, when there is still time to fix them before
  the business day?
- Problem record: if Monday mornings keep coming in RED, this is a
  problem to fix (earlier checks, automated alerts, renewal
  automation), not an incident to repeat.
