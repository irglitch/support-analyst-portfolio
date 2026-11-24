# Day 18 — RCA Document Generator

## 📟 The situation (real-world use case)

**Tuesday, 09:20 — the morning after the outage.** INC-2011 (P1 —
checkout returning HTTP 500s, Monday 09:02–10:47) is resolved, and the
duty manager needs the root-cause analysis document for the business
review tomorrow. Until now an RCA meant copying the timeline out of the
ticket, re-typing the impact numbers from three different places and
hoping nothing was missed — and a review that finds a hole sends the
whole document back, usually the night before the meeting.

This project closes the loop on the earlier days: the timeline and the
evidence come from the tools already built — the Day 01 log triage, the
Day 13 health-check probes, the Day 08 duplicate-transaction check —
and this tool turns them into a document the business can actually read.

## 🔧 The fix

`rca_generator.py` reads one incident file (JSON — see
`sample_data/incident.json`) and writes a structured RCA document from
a Markdown template (`template.md`, also the built-in default):

- **Executive summary** — what happened, in plain language
- **Impact** — users affected, failed transactions, business impact,
  how it was detected
- **Timeline** — every event with elapsed time since detection
  (pre-detection events, like the change that caused it, show "—")
- **Root cause** and a **5-whys chain** — each "why" must lead to the
  next; a chain shorter than 3 levels is flagged as too shallow
- **What went well / what went badly** — the honest part, including
  the 45-minute SLA breach
- **Action items** — each with an owner, a due date and a status
- **Evidence** — the logs and checks the claims rest on
- **Follow-up** — what happens next, and what triggers an escalation

The completeness check is the point of the tool. A **P1 RCA is not
FINAL** until every required section is present — root cause, 5 whys,
business impact, evidence, and every action item with an owner and a
due date. Anything missing stamps the document **DRAFT** and the tool
exits non-zero, with a checklist of what still needs filling in — so
an incomplete RCA can never be sent to the business by accident. P2/P3
incidents are allowed to omit the 5-whys chain.

## ▶️ Run it

```bash
cd projects/day-18-rca-document-generator
python3 rca_generator.py sample_data/incident.json --template template.md --out output/RCA-INC-2011.md --generated-at "2026-11-24 09:20"
cat output/RCA-INC-2011.md
```

Or with the built-in template and default output path:

```bash
python3 rca_generator.py sample_data/incident.json
```

**Result on the sample data:** **FINAL** — the RCA for INC-2011 is
complete. The story it tells:

- **What:** checkout-api returned HTTP 500 for most checkout attempts,
  Monday 09:02–10:47 — **1h 45m**, 1,240 failed checkouts, ~1,850
  customers affected, ~$38,450 of checkout value interrupted
- **Root cause:** connection-pool exhaustion. CHG-8841 (applied 02:15
  Sunday night) cut the database connection pool from 200 to 50 with
  no load test against Monday-morning peak traffic; at 09:02 the pool
  saturated, requests queued behind the 30-second timeout, and
  checkout failed
- **Detection was fast** — the Day 13 probe alerted at 09:02, nine
  minutes before the first customer report; log triage (Day 01)
  narrowed it to DB timeouts by 09:35
- **What went badly:** the change had no rollback trigger on the pool
  setting, there was no pool-exhaustion runbook (23 minutes spent
  confirming what a checklist would have shown in five), and the P1
  breached its 60-minute SLA by 45 minutes
- **The reassuring fact, verified:** the Day 08 duplicate check ran
  before closure — **0 double-charges**, so the business could be told
  confidently that nobody was charged twice
- **Actions:** 4 items with owners and due dates — a mandatory load
  check for connection-limit changes (due 2026-12-04), a pool-usage
  alert at 80% (due 2026-11-27), a pool-exhaustion runbook (due
  2026-11-26, in progress), and a review of the CHG-8841 approval
  (due 2026-11-28)

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Root cause analysis & 5-whys · Incident documentation for business
review · Timeline reconstruction from logs and change records · Impact
quantification (users, transactions, business value) · SLA awareness ·
Action-item ownership & follow-up · Python scripting (JSON, Markdown
templates, validation) · Turning earlier monitoring tools into
evidence for a review

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this RCA: verify,
escalate, communicate, and the follow-up that stops it happening again.

*Practice scenario with sample data, built for this portfolio — not employer work.*
