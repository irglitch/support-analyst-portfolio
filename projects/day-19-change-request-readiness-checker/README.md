# Day 19 — Change Request Readiness Checker

## 📟 The situation (real-world use case)

**Wednesday, 09:20 — the day before CAB.** The change manager asks
support to review Thursday evening's five change requests before the
Change Advisory Board approves them. The lesson of Monday's outage is
still fresh: INC-2011 (Day 18) happened because CHG-8841 cut a database
connection pool from 200 to 50 with **no load test and no rollback
trigger** — checkout was down for 1h 45m. Reviewing five change tickets
by hand means re-reading every field of every ticket, and the missing
rollback trigger is exactly the field that gets skimmed at 09:20.

## 🔧 The fix

`change_readiness.py` reads the change requests (JSON — see
`sample_data/change_requests.json`) and runs the readiness checks
support applies before a change is approved:

- **Description, risk, impact** — CAB cannot approve what it cannot
  understand; the affected services must be named
- **Test evidence** — tested in a non-production environment and passed
- **The CHG-8841 rule** — high-risk changes, and anything that moves a
  limit (pool size, timeout, quota), need **load-test evidence**
- **Rollback** — a plan, a trigger that is a real condition (a trigger
  written as "TBD" is not a trigger), and an estimated rollback time
- **Window maths** — the scheduled window must fit implementation
  *plus* rollback; a window that fits with no room for trouble is a
  warning, one that cannot fit the rollback is a blocker
- **Approvals** — approved, by someone other than the implementer, and
  CAB-approved when the risk is high
- **Communications, dependencies, peer review, verification** — an
  expected outage with no stakeholder notice blocks; a missing notice
  on a quiet change is a condition CAB can accept

Each change gets a verdict — 🟢 **READY**, 🟡 **READY WITH
CONDITIONS**, or 🔴 **NOT READY** — and the report ends with a ranked
action list (blockers first) CAB can work through. Exit codes are
0 (all ready) / 1 (conditions or blockers) / 2 (input error), so a
scheduler can gate the CAB pack on it. A `--change CHG-xxxx` flag
re-checks a single change after its blockers are fixed. The tool only
reads and reports — it never approves, schedules, or implements a
change; those calls belong to CAB.

## ▶️ Run it

```bash
cd projects/day-19-change-request-readiness-checker
python3 change_readiness.py sample_data/change_requests.json --out output/change_readiness_report.md --generated-at "2026-11-25 09:20"
cat output/change_readiness_report.md
```

**Result on the sample data:** 🔴 **NOT READY** — 2 of 5 changes
blocked (3 blockers, 3 warnings), exit code 1:

- 🟢 **CHG-8901 — Payment gateway connection pool 50 → 120** (the
  INC-2011 follow-up) is **READY**: high risk done properly — load
  tested at 1.5× Monday peak (pool peaked at 71 of 120), rollback
  trigger defined (error rate above 2% for 5 minutes), CAB approved,
  and implementation + rollback uses only 40m of the 90m window
- 🔴 **CHG-8902 — Settlement service v2.4 deploy** is **NOT READY**:
  the rollback trigger is still "TBD" and the service-owner approval
  is outstanding — the same two gaps that turned CHG-8841 into a P1
- 🟡 **CHG-8903 — CRM sync retry patch** is **READY WITH
  CONDITIONS**: stakeholders not yet notified (no outage expected) and
  no peer review recorded
- 🔴 **CHG-8904 — Reporting database index** is **NOT READY**: the
  maths does not fit — 50m implementation + 20m rollback = 70m in a
  60m window, so there would be no time to back out; dependencies are
  also unchecked
- 🟢 **CHG-8905 — Notification service TLS renewal** (standard, low
  risk) is **READY** — correctly *not* flagged for load-test or CAB
  evidence, because a standard low-risk change needs neither

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Change management & CAB readiness · Risk assessment and the load-test
rule for limit changes · Rollback planning (plan, trigger, and window
maths) · Separation of duties in approvals · Blocker-vs-condition
judgement · Python scripting (JSON validation, exit-code gating) ·
Turning an RCA action item (Day 18) into a preventive control

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify,
escalate, communicate, and the follow-up that stops the next CHG-8841.

*Practice scenario with sample data, built for this portfolio — not employer work.*
