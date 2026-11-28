# Day 22 — SLA Breach Early Warning

## 📟 The situation (real-world use case)

**Saturday, 09:20 — the weekend on-call check.** Nine tickets are
open, and the queue looks calm: only one deadline has passed. But
Day 05's tracker answers "what has breached?" — by then the SLA is
already lost. The question that saves the weekend is earlier:
*what will breach if nothing changes?* INC-3201, the checkout P1,
has 20 minutes of SLA clock left and 90 minutes of work remaining —
it breaches at 09:40 on current pace, however green it looks.
INC-3202's settlement file is blocked on a bank resend with no
update in over three hours. INC-3206 has sat unassigned since
yesterday afternoon. None of those show up in a breached-only list
until it is too late to fix them.

## 🔧 The fix

`sla_early_warning.py` reads the open queue (JSON — see
`sample_data/open_tickets.json`) and, for each ticket, forecasts a
finish time — now plus the assignee's estimated remaining work —
and compares it with the SLA deadline (P1: 4h, P2: 8h, P3: 24h,
P4: 48h):

- **🔴 BREACHED** — past deadline; the forecast no longer matters,
  recovery and communication do
- **🟠 WILL BREACH** — forecast finish is past the deadline while
  clock remains: the ticket breaches on current pace, and the
  report says by how much and how much clock is left to act in
- **🟡 AT RISK** — forecast is fine but a slow-motion signal is
  not: no update beyond the priority's threshold (P1 30m, P2 1h,
  P3 4h, P4 8h), unassigned aging, or blocked on a vendor
- **🟢 ON TRACK** — forecast inside the deadline with a fresh
  update, so the weekend check can ignore it safely
- **Assignee overload** — one person holding 3+ warned tickets is
  flagged, because rebalancing is itself breach prevention
- Every warning names its action — escalate, add help, chase the
  blocker, assign an owner — while the action can still matter.
  Exit codes: 0 = nothing to do, 1 = warnings, 2 = a breach (or
  input error), so a scheduler can run the sweep hourly

The tool only reads and warns — it never edits, reassigns, or
closes a ticket. And it is honest about its input: a forecast is
only as good as the estimate behind it, which is why a stale
ticket's "30 minutes remaining" is flagged as possibly fiction.

## ▶️ Run it

```bash
cd projects/day-22-sla-breach-early-warning
python3 sla_early_warning.py sample_data/open_tickets.json --out output/sla_early_warning_report.md
cat output/sla_early_warning_report.md
```

Re-check the same queue later in the day:

```bash
python3 sla_early_warning.py sample_data/open_tickets.json --now 2026-11-28T11:00 --out output/sla_early_warning_report.md
```

**Result on the sample data (checked at 09:20):** 🔴 **BREACH —
1 already breached, 2 forecast to breach, 3 at risk**, exit code 2:

- 🔴 **INC-3203** (CRM sync, P2) breached 2h 20m ago at 07:00 —
  escalate with a recovery plan, not a forecast
- 🟠 **INC-3201** (checkout 500s, P1) **will breach**: forecast
  finish 10:50 is 1h 10m past the 09:40 deadline, with only 20m
  of clock left — add help now or declare the breach honestly
- 🟠 **INC-3208** (stale search, P2) will breach by 40m — 2h 40m
  of clock remains, enough to act if it is acted on now
- 🟡 **INC-3202** is blocked on the bank's file resend with no
  update for 3h 10m; **INC-3204** has had no update in 20h 20m
  at 10% progress; **INC-3206** is unassigned after 18h 20m
- 🟢 INC-3205, INC-3210 and INC-3207 are on track — and Sam R
  holds all three of the breached/will-breach tickets, so the
  overload flag fires: rebalancing one is a breach-prevention
  action in itself

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

SLA breach prevention (forecasting, not just reporting) · Incident
prioritisation under time pressure · Spotting stale, unassigned
and vendor-blocked tickets before they breach · Workload balancing
as a support action · Python scripting (datetime arithmetic,
exit-code gating) · Escalation with evidence

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify,
escalate, communicate, and the follow-up that turns a Saturday
surprise into an hourly sweep.

*Practice scenario with sample data, built for this portfolio — not employer work.*
