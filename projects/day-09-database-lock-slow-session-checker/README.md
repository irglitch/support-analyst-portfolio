# Day 09 — Database Lock / Slow Session Checker

## 🔒 The situation (real-world use case)

**Sunday, 09:20.** Users report the app is slow and checkouts are hanging —
payments sit "processing" and never complete. The app servers look fine,
so the next place to look is the database: is one session holding a lock
that everyone else is waiting on? Reading a session list by hand means
scanning 14 sessions, matching each blocked session to its blocker, and
doing the time arithmetic — while the checkout queue grows and the SLA
clock runs.

## 🔧 The fix

`session_checker.py` loads a database session snapshot (CSV) into SQLite
(Python stdlib only) and runs the queries in `locks.sql`:

- **Headline counts** — sessions, active, blocked, idle, longest-running
- **Blocking chains** — which sessions are blocking others, how many each
  one holds up, and the longest wait (self-join on `blocking_session_id`)
- **Blocked sessions** — who is waiting, on which session, and for how long
- **Long-running active sessions** — running over **10 minutes**
- **Idle-in-transaction sessions** — sitting in an open transaction over
  **5 minutes**, still holding their locks
- **Watch list** — active sessions between 2 and 10 minutes, not flagged
  but worth a second look

The tool only reads the snapshot and reports — it never kills a session.
Killing one is a DBA decision, with the business impact weighed first.

## ▶️ Run it

```bash
cd projects/day-09-database-lock-slow-session-checker
python3 session_checker.py sample_data/sessions.csv --out output/session_report.md
cat output/session_report.md
```

The queries themselves live in `locks.sql` — the tool loads the CSV into a
`sessions` table and runs each statement in order, so the SQL is readable
and reusable on its own. (In a real environment the snapshot would come
from the database's session view — e.g. `pg_stat_activity` in PostgreSQL
or `v$session` in Oracle — exported to the same CSV shape.)

Exit codes: `0` = healthy, `1` = blocking chain or slow sessions found
(a scheduler can page on this), `2` = error.

**Result on the sample data:** 14 sessions in the snapshot — 7 active,
4 blocked, 3 idle — with a 🔴 **BLOCKING CHAIN**:

| Blocker | Running | Blocking | Longest waiter |
|---|---|---|---|
| SESS-101 — overnight settlement batch | 42m 0s | 3 sessions | 10m 40s |
| SESS-102 — checkout-api, idle in transaction | 18m 0s | 1 session | 9m 0s |

The overnight settlement batch (SESS-101) has been updating the
`transactions` table for 42 minutes, holding up three checkout and
billing sessions — including a payment insert (SESS-104) waiting
10m 40s. A second chain: SESS-102 updated an order 18 minutes ago and
then sat idle in its transaction, blocking the shipment update
(SESS-108). A reporting query (SESS-103) has also been running 12
minutes — slow, but blocking nobody. Two more sessions are on the watch
list (6m 20s and 2m 10s).

Run the tests:

```bash
python3 -m unittest discover -s tests -v
```

## 🛠 Skills demonstrated

SQL (self-join, GROUP BY, aggregate functions) · Database lock / blocking
analysis · Session triage (blocked vs blocker vs long-running vs idle) ·
Python + SQLite · Escalation with named session IDs · Support documentation

## 📖 Support process

See [RUNBOOK.md](RUNBOOK.md) — what to do with this report: verify, escalate, communicate, RCA.

*Practice scenario with sample data, built for this portfolio — not employer work.*
