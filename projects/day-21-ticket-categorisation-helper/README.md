# Day 21 — Ticket Categorisation Helper

## 📟 The situation (real-world use case)

**Friday, 09:20 — morning triage.** Eight tickets landed overnight,
and the queue is lying. TKT-3101 says checkout returns HTTP 500 for
all customers and revenue has stopped — but it was logged as a
low-priority "General" query, below a password reset. TKT-3102 is a
second report of the same checkout failures. A missing settlement
file is categorised as an application error, so it would sit in the
wrong queue while the batch waits. And TKT-3107 says only "system
slow", with no service named. Working the queue in arrival order
means the outage waits behind the password reset. Triage first: what
is it, how urgent is it really, and which queue owns it?

## 🔧 The fix

`ticket_categorisation.py` reads the morning queue (JSON — see
`sample_data/tickets.json`) and, for each ticket, scores transparent
keyword rules over the subject and description to suggest:

- **Category and routing queue** — specific phrases ("settlement
  file", "template not found") outweigh generic words ("error"), so
  a vague ticket scores low instead of being forced into a category
- **Priority from impact signals, not the reporter's guess** — wide
  impact ("all customers", "nobody can", revenue stopped) or a
  failure signal with 100+ affected users suggests P1; a large user
  count alone does not (a certificate expiring Monday is urgent,
  not an outage)
- **Disagreements with the ticket as logged** — miscategorised,
  priority too low or too high, and possible hidden P1s flagged
  first
- **Likely duplicates** — same service plus a shared error code or
  shared subject words, so two reports of one outage are worked
  once, not twice
- **Human review instead of a guess** — low confidence, a tie, or
  too little detail sends the ticket to the analyst with the
  question to ask the reporter

Every suggestion shows the keywords that drove it, so the analyst
can agree or overrule in seconds. Exit codes are 0 (queue clean) /
1 (actions found) / 2 (input error), and `--ticket TKT-xxxx`
re-checks a single ticket after its details are corrected. The tool
only reads and suggests — it never edits, merges, or closes a
ticket; those calls stay with the analyst on triage.

## ▶️ Run it

```bash
cd projects/day-21-ticket-categorisation-helper
python3 ticket_categorisation.py sample_data/tickets.json --out output/ticket_categorisation_report.md --generated-at "2026-11-27 09:20"
cat output/ticket_categorisation_report.md
```

**Result on the sample data:** 🔴 **Actions needed — 6 items**
(5 tickets + 1 duplicate pair), exit code 1:

- 🔴 **TKT-3101** is a **hidden P1**: "all customers", "nobody can",
  revenue stopped, 1,200 affected — re-categorise General →
  Incident — Service Outage, raise P3 → P1, work it first
- 🔴 **TKT-3102** is the same outage reported again (checkout 500s,
  PAY-3002, 300 affected) — also P1, and flagged as a **likely
  duplicate of TKT-3101**: link the reports, keep one master ticket
- 🔴 **TKT-3104** is miscategorised: the missing settlement file is
  **Batch & File Transfer**, not an application error — re-route
  and raise P3 → P2, the batch is blocked today
- 🔴 **TKT-3108** (portal certificate expires Monday) raises
  P3 → P2 — urgent, but correctly *not* P1: nothing is down yet
- 🔴 **TKT-3107** ("system slow", no service named) goes to
  **human review** — the tool asks for the service and symptom
  instead of guessing
- 🟢 TKT-3103 (password reset), TKT-3105 (invoice-export template
  error — Day 20's CHG-8854 fallout, already P2) and TKT-3106
  (month-end how-to) are categorised and prioritised correctly —
  no action

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Incident triage and prioritisation · Impact/urgency-based priority
setting (and spotting a hidden P1) · Category and routing-queue
assignment · Duplicate detection across reports · Knowing when
*not* to automate a decision (low-confidence → human review) ·
Explainable rules (every suggestion shows its evidence) · Python
scripting (keyword scoring, exit-code gating)

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify,
escalate, communicate, and the follow-up that stops the next outage
arriving as a "General" query.

*Practice scenario with sample data, built for this portfolio — not employer work.*
