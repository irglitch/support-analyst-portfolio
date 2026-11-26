# Day 20 — Deployment Verification Checker

## 📟 The situation (real-world use case)

**Thursday, 09:20 — the morning after the deployment window.** The
change manager wants last night's six change tickets closed before the
10:00 settlement batch. Every deployment tool reported "success", but
that is not proof the changes are live: one instance can still run the
old build, a renewed certificate can sit in the vault while the
endpoint serves the old one, and a feature flag can be on while the
feature returns HTTP 500. Closing the tickets on the deployment tool's
word is how "deployed" becomes next week's incident. Support verifies
first — and the same checks will close tonight's payment-pool fix
(CHG-8901, Day 19) tomorrow morning.

## 🔧 The fix

`deployment_verification.py` reads the night's deployments (JSON — see
`sample_data/deployments.json`): what each change was *supposed* to do
(the CAB decision) against what is *observed* this morning. It checks:

- **Outcome** — a change CAB approved must show a completed deployment;
  a change CAB **held** must show no deployment and an unchanged
  version ("correctly not deployed" is a result worth proving)
- **Every instance** — the new version and config values must read back
  on *all* instances; one instance on the old build is a **partial
  deployment**, not a deployment, and a missing instance cannot be
  verified at all
- **Health and smoke test** — the service must answer healthy and the
  end-to-end check the change promised must have run and passed; a
  deployment nobody exercised is not verified
- **Error rate** — above the warning level is a condition to watch;
  above the change's own **rollback trigger** the plan says back out
- **Certificate** — the live endpoint must serve the new certificate,
  not just have it sitting in the vault
- **Window** — finishing late is recorded on the ticket as a warning,
  not treated as a failure of the change itself

Each deployment gets a verdict — 🟢 **VERIFIED**, 🟡 **VERIFIED WITH
WARNINGS**, or 🔴 **FAILED** — and the report ends with a ranked action
list (failures first). Exit codes are 0 (all verified) / 1 (warnings or
failures) / 2 (input error), so a scheduler can gate ticket closure on
it. A `--deployment CHG-xxxx` flag re-checks a single deployment after
its fix. The tool only reads and reports — it never deploys, restarts,
or rolls back anything; those calls belong to the change owner and the
duty manager.

## ▶️ Run it

```bash
cd projects/day-20-deployment-verification-checker
python3 deployment_verification.py sample_data/deployments.json --out output/deployment_verification_report.md --generated-at "2026-11-26 09:20"
cat output/deployment_verification_report.md
```

**Result on the sample data:** 🔴 **FAILED** — 3 of 6 deployments not
verified (4 failures, 1 warning), exit code 1:

- 🟡 **CHG-8851 — Checkout API v3.2.1** is **VERIFIED WITH
  WARNINGS**: v3.2.1 live on all 3 instances, smoke checkout passed,
  error rate 0.4% — but it completed at 23:41, 11 minutes after the
  window closed; record the overrun and close
- 🟢 **CHG-8852 — Settlement service v2.3.1** is **VERIFIED**: version
  and `retry_limit = 5` read back on both instances, test settlement
  file processed, inside the window
- 🔴 **CHG-8853 — Search API v5.0** **FAILED**: partial deployment —
  `search-03` still runs v4.7.2 while the other two run v5.0.0, so
  search results are inconsistent depending on which instance answers
- 🔴 **CHG-8854 — Billing invoice-export flag** **FAILED** twice: the
  smoke test returned HTTP 500 (template not found) and the error rate
  is 6.4%, past the 5.0% rollback trigger — roll the flag back per the
  change plan
- 🔴 **CHG-8855 — Customer portal TLS renewal** **FAILED**: the live
  endpoint still serves the old certificate (expires 2026-12-10) — the
  renewal reached the vault but the service was never restarted onto
  it
- 🟢 **CHG-8856 — Reporting database index** is **VERIFIED**: CAB held
  it, and it correctly did not deploy — schema unchanged at
  schema-114

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Post-implementation verification & change closure · Partial-deployment
detection across instances · Smoke testing and rollback-trigger
judgement · Certificate lifecycle verification (live vs vault) ·
Verifying CAB deferrals held · Python scripting (JSON validation,
exit-code gating) · Closing the loop Day 19 opened (readiness before
CAB, verification after the window)

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify,
escalate, communicate, and the follow-up that stops the next silent
partial deployment.

*Practice scenario with sample data, built for this portfolio — not employer work.*
