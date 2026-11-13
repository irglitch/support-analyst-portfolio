# Day 07 — Error Code Knowledge Base

## 📟 The situation (real-world use case)

**Friday, 09:20 — the helpdesk phone rings.** *"Checkout is failing
with a timeout again."* Every support team has seen most errors
before — the fix is usually already written down in an old ticket.
The problem is finding it: the last fix for this exact error lives in
a ticket from three weeks ago, and nobody remembers the ticket
number. So the analyst starts the investigation from zero, asks the
user the same questions the last analyst asked, and re-discovers the
same root cause — while the checkout stays broken and the SLA clock
runs.

## 🔧 The fix

`error_kb.py` is a small, searchable knowledge base of past
incidents, stored as plain JSON so any analyst can read and update
it. Each entry records an error code, the system it belongs to, the
symptom, the root cause, and the fix that worked last time — with
the original ticket and how many times the error has been seen:

- **`search <query>`** — search by error code (`ORA-12154`) or by a
  word from the symptom (`timeout`). Results are ranked: an exact
  error-code match first, then a code substring, then keyword matches
  in the symptom / cause / fix. Within each rank, the fix seen most
  often comes first — the fix that worked six times beats the one
  that worked once.
- **`list [--system NAME]`** — browse the whole base, or one system.
- **`stats`** — totals, entries per system and severity, and the
  three most-seen errors (the ones worth memorising).

**Exit codes a scheduler or a wrapper script can use:** 0 = match(es)
found, 1 = no match, 2 = usage or file error. The tool never changes
anything in production — it only tells the analyst what worked last
time.

## ▶️ Run it

```bash
cd projects/day-07-error-code-knowledge-base
python3 error_kb.py sample_data/knowledge_base.json search timeout --out output/kb_report.md
cat output/kb_report.md
```

Search by exact error code:

```bash
python3 error_kb.py sample_data/knowledge_base.json search ORA-12154
```

Browse one system, and see the headline numbers:

```bash
python3 error_kb.py sample_data/knowledge_base.json list --system CRM
python3 error_kb.py sample_data/knowledge_base.json stats
```

**Result on the sample data (checked at 09:20):** searching
`timeout` returns **3 matches**. The top match is **PAY-3002** —
card authorisation fails with a gateway timeout, seen **6 times**
(last fixed 2026-10-22, INC-1048): check the vendor status page
first, retry with back-off, queue the failures — and do not
re-charge the customer twice. Next is **DB-1045** — checkout
database connection timeout, seen **5 times** (INC-1042): the
overnight batch held the connection pool open; kill the idle batch
sessions and restart the pool, *don't* restart the app first. Third
is **RPT-207** — monthly report timeout (INC-1015): add a date
filter and schedule it off-peak. The base holds **12 entries across
8 systems, seen 44 times in total** (P1: 3, P2: 4, P3: 5). The
analyst now has a tried fix in seconds instead of a fresh
investigation.

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

Incident knowledge management · Error-code triage · Searching past
incidents before re-investigating · JSON data handling · Python
scripting · Support documentation · Escalation with evidence

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
