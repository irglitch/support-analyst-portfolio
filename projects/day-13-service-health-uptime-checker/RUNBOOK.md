# RUNBOOK — Day 13: Service Health / Uptime Checker

## 1. Verify

- Run the tool and read the verdict first: 🔴 CRITICAL means a
  critical service is down *right now* — act before reading the
  rest. 🟡 DEGRADED means something is slow or under SLA but still
  answering. 🟢 ALL HEALTHY means file the report and move on.
- **"Down" means failing now, not failed once.** In the sample data
  `crm-sync` failed 6 consecutive probes — that is an outage, not a
  blip. `payment-api` failed one probe at 03:20 and recovered; its
  99.65% uptime is still inside SLA, so it is UP, not an incident.
  Don't escalate a single failed probe.
- **"Up" does not mean healthy.** `settlement-service` answered
  every probe in the window (100% uptime) but averages 1,279 ms
  against an 800 ms threshold. If you only check up/down, you miss
  the service that is about to become the next incident.
- Check the outage start time against the first user report. In the
  sample data `crm-sync` started failing at 08:55 and users called
  at 09:00 — the probe log proves the outage came first, so the
  reports are symptoms, not a separate problem.
- If a service shows ⚪ UNKNOWN, the prober may be the problem, not
  the service. Check the probe log itself before declaring the
  service down — no data is not the same as failed data.
- If the tool exits `2`, the inputs are the problem — a missing
  file, a bad timestamp, or a probe for a service that isn't in the
  inventory. Fix the file, don't hand-edit the report.

## 2. Escalate (with facts)

- **Critical service DOWN (sample data):** tell the platform team
  the exact facts — "crm-sync has been down since 08:55 (25
  minutes), 6 consecutive failed probes, last error 'Connection
  refused', uptime 97.92% against a 99.5% SLA. Users are seeing
  stale CRM data since 09:00." A restart decision is theirs; your
  job is to make it a 30-second decision.
- **Service DEGRADED on latency (sample data):** raise it with the
  service owner, not as an incident — "settlement-service is up
  with 100% uptime but averaging 1,279 ms against an 800 ms
  threshold, p95 1,567 ms. Settlements are running slow; is this a
  load problem or a downstream dependency?" Include the numbers so
  they don't have to re-measure.
- **One blip, still UP:** don't escalate. Note it in the BAU log —
  "payment-api had a single connection timeout at 03:20, recovered
  immediately, uptime 99.65% inside SLA" — so the next person
  doesn't re-investigate it.
- Escalate with the service name, the outage start time, the
  consecutive-failure count, and the last error — "crm-sync down
  since 08:55" gets a response; "the CRM is broken" starts a fresh
  investigation.

## 3. Communicate

- Tell the business what is down and since when, in one message:
  "CRM sync has been down since 08:55 — customer data in the CRM
  is up to 25 minutes stale. The platform team is on it. Payment
  and settlement services are unaffected."
- Tell users what is *not* broken too: payment-api, the customer
  portal, the file gateway and notifications are all up, so a user
  whose checkout works is not imagining it — only the CRM sync is
  affected.
- Don't promise a fix time you don't have. Say what happens next
  instead: "The next health check runs in 5 minutes; I'll update
  this thread when crm-sync answers again."

## 4. After recovery

- Re-run the checker once the service answers again and keep both
  reports — the before/after pair is the incident record, and the
  outage duration comes from the probe log, not from memory.
- Confirm the recovery is real, not one good probe: the service
  needs several consecutive successful probes *and* latency back
  under threshold before you tell the business it's fixed.
- Check the degraded service again after the incident: if
  settlement-service is still averaging over 800 ms once crm-sync
  is back, it was never a knock-on effect — it needs its own
  follow-up with the service owner.
- If the same service fails again tomorrow, raise it as a
  reliability issue: a service that drops off the probe log two
  mornings running is a pattern, not bad luck.

## 5. RCA prompts

- Why did crm-sync start refusing connections at 08:55 — was it
  restarted, did a certificate or credential expire, or did a
  deployment land just before?
- The outage was visible in the probe log at 08:55 but nobody
  looked until users called at 09:00 — should the health check
  alert on 2 consecutive failures instead of waiting for the 09:20
  manual run?
- settlement-service latency is 1,279 ms against an 800 ms
  threshold with zero failures — is the threshold still right for
  current volumes, or is the service genuinely degrading?
- payment-api and file-gateway each had one isolated timeout in
  the night — same cause, or coincidence? One blip each is noise;
  the same error at the same time would be a shared dependency.
