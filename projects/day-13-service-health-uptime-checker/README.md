# Day 13 — Service Health / Uptime Checker

## 🖥️ The situation (real-world use case)

**Thursday, 09:20.** The morning BAU health check. Six internal
services are probed every 5 minutes and the results land in a probe
log — but nobody has looked at it yet this morning. At 09:00 users
start reporting that the CRM is showing stale customer data, and the
duty manager asks the one question support has to answer before the
business day starts: *which services are actually up, which are slow,
and which are down?* "The CRM feels slow" could be a dead service, a
slow dependency, or nothing at all — and guessing wrong means either
escalating a non-incident or ignoring a real outage.

## 🔧 The fix

`health_check.py` (Python stdlib only) reads the service inventory
(`services.json` — URL, expected status, latency threshold, uptime
SLA, critical or not) and the last 24 hours of probe results
(`probes.csv` — 1,728 rows, one probe every 5 minutes per service),
then produces a one-page **Service Health / Uptime Report**:

- **Per-service status** — 🟢 UP, 🟡 DEGRADED, 🔴 DOWN, ⚪ UNKNOWN
  (no probes in the window at all)
- **Uptime vs SLA** — successful probes / total probes, compared
  against each service's own SLA
- **Latency** — average and p95 against the service's threshold.
  A service answering in 1,279 ms against an 800 ms threshold is
  up, but it is not healthy
- **Outage detail** — when the current failure run started, how
  long it has lasted, how many consecutive probes failed, and the
  last error seen, so the escalation names facts, not guesses
- **One overall verdict** — 🟢 ALL HEALTHY, 🟡 DEGRADED, or
  🔴 CRITICAL when a critical service is DOWN

The tool only reads the probe log and reports — it never restarts a
service or clears an alert. Restarting is the platform team's call;
support supplies the evidence.

## ▶️ Run it

```bash
cd projects/day-13-service-health-uptime-checker
python3 health_check.py sample_data/services.json sample_data/probes.csv --out output/health_report.md
cat output/health_report.md
```

Exit codes: `0` = ALL HEALTHY, `1` = DEGRADED or CRITICAL,
`2` = error (missing file, bad row, probe for an unknown service).

**Result on the sample data:** 🔴 **CRITICAL — a critical service
is DOWN.** `crm-sync` has failed 6 consecutive probes since 08:55
(25 minutes, last error "Connection refused"), uptime 97.92%
against a 99.5% SLA — that is the stale-CRM symptom users reported
at 09:00, and it started 5 minutes before the first user call.
`settlement-service` is 🟡 DEGRADED: 100% uptime, but average
latency 1,279 ms against an 800 ms threshold (p95 1,567 ms), so
settlements are running slow even though nothing has failed. The
other four services are 🟢 UP — `payment-api` survived a single
timeout blip at 03:20 (99.65% uptime) and `file-gateway` a single
gateway timeout at 06:10 (99.65%), both still inside SLA.

## ✅ Tests

21 unittest tests, all passing:

```bash
python3 -m unittest discover -s tests
# Ran 21 tests in 0.129s — OK
```

Tests cover: the sample-data verdict (CRITICAL, crm-sync DOWN since
08:55, settlement-service DEGRADED on latency, four services UP),
status classification (UP / DEGRADED / DOWN / UNKNOWN), consecutive-
failure counting, uptime vs SLA, latency thresholds, p95 maths,
non-200 statuses counting as failures, and input errors (missing
file, probe for an unknown service, bad timestamp) plus the CLI
exit codes.

## 🛠 Skills demonstrated

Service monitoring & uptime reporting · SLA tracking · Latency
analysis (average / p95) · Incident triage (down vs degraded vs
healthy) · Python scripting · Support documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
