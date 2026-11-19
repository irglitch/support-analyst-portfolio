# Interview Talking Points — How to Use This Portfolio Honestly

**The one-line opener:** "Alongside my 10+ years of support experience, I build a small
production-support scenario every day — here's one that mirrors a ticket type I've
handled: stuck transactions caused by a database connection failure."

## For Day 01 — Log Triage Analyzer
- **Situation:** Users report a symptom ("stuck in Pending"). Support's job is to find
  the failing layer fast, under SLA pressure.
- **Action:** I wrote a small Python tool that groups log errors by service and error
  code, with first/last seen, and suggests a priority — turning a 45-minute manual
  search into a one-page report I can paste into the ticket.
- **Result (in the scenario):** The dominant error is a DB connection timeout starting
  *before* the first user call — so escalation goes to the DB/infra team with evidence,
  and the knock-on file issue is tracked separately instead of being mistaken for the cause.
- **What it shows:** Triage thinking, not just coding — symptom vs. cause, escalation
  with facts, communication cadence, and RCA follow-up (see the runbook).

## For Day 02 — Linux Health Check Script
- **Situation:** Users report a vague symptom ("the app is slow") with no error
  message. Support's first job is to turn "slow" into facts before escalating.
- **Action:** I wrote a Bash script that runs the standard first-response checks —
  CPU load per core, memory, swap, disk space, top processes, and key service
  status — and writes a one-page PASS / WARN / FAIL report with an exit code
  monitoring can use. It also replays against a captured snapshot, so the same
  checks work on saved output from a server you can't reach right now.
- **Result (in the scenario):** The slow server fails three checks — root disk 92%
  full, load 2.10 per core, and the payment-api service stopped — with memory at
  88% and the app process itself burning 87% CPU. The vague "slow" becomes a
  concrete escalation: clear the disk, find why the service stopped, then restart it.
- **What it shows:** First-response triage under pressure, Linux basics, and
  escalating with evidence instead of a guess (see the runbook).

## For Day 03 — SQL Reconciliation Break Finder
- **Situation:** Finance reports the daily totals don't match — billing says
  $3,540.23, the ledger says $3,476.00 — and month-end close is blocked until
  the gap is explained. Both extracts have 16 transactions, so counting rows
  doesn't help.
- **Action:** I loaded both extracts into SQLite and ran reconciliation queries
  — totals per system, billed-but-never-posted, posted-but-never-billed, and
  same-transaction-different-amount — storing money as integer cents so the
  totals are exact. The tool writes a one-page report naming every break.
- **Result (in the scenario):** Exactly 4 transactions explain the whole
  $64.23 gap — one missing posting ($145.00), one orphan posting ($89.50),
  and two amount mismatches including a transposed digit ($210.00 vs $201.00).
  13 of 16 transactions match exactly, so finance chases 4 rows instead of
  re-checking the whole day.
- **What it shows:** SQL JOINs and the LEFT JOIN anti-pattern, reconciliation
  thinking, exact money handling, and escalating with named transactions
  instead of just a gap figure (see the runbook).

## For Day 04 — File Transfer Monitor
- **Situation:** The daily settlement file is due by 07:00 — finance
  reconciles against it and the downstream batch can't start without it.
  At 07:30 it still hasn't arrived, and checking the morning's four files
  by hand (transfer log, folder listing, timestamps, sizes) takes 15–20
  minutes and can miss a zero-byte file that *looks* like it arrived.
- **Action:** I wrote a Python tool that checks an expected-files manifest
  against the morning's transfer log and the real drop folder, and writes a
  one-page status report — OK / LATE / MISSING / EMPTY / SMALL per file —
  with an overall status and an exit code (0/1/2) a scheduler can use.
  It also flags files in the log but not on disk, and files that arrived
  without being in the manifest.
- **Result (in the scenario):** 🔴 ALERT — of 4 expected files only 1 is
  OK. The critical settlement file is MISSING, the audit log arrived as a
  zero-byte file (a failed transfer), and the FX rates file is 47 minutes
  late. An unexpected promo-codes file also needs confirming with the
  sender. Finance and the batch owners get the facts at 07:30 instead of
  finding out at 09:00.
- **What it shows:** Batch/settlement-file support, SLA awareness,
  verifying on disk instead of trusting the log alone, and escalating
  with named files and business impact instead of "the file is missing"
  (see the runbook).

## For Day 05 — Incident SLA Tracker
- **Situation:** At the 09:20 morning SLA review, ten incidents are open
  and nobody has checked the clock. The duty manager asks which tickets
  are breaching and which are about to — answering by hand means opening
  every ticket, remembering each priority's SLA target, and doing the
  arithmetic ten times over.
- **Action:** I wrote a Python tool that reads the incident export (CSV),
  works out each open ticket's resolution deadline from its priority's SLA
  target (P1: 4h, P2: 8h, P3: 24h, P4: 48h), and writes a one-page report
  sorted by deadline — BREACHED, AT RISK (under 2 hours or under 25% of
  the target left), or ON TRACK — with exit codes (0/1/2) a scheduler can
  page on. Resolved tickets are excluded; unknown priorities are flagged
  for a manual check instead of crashing the run.
- **Result (in the scenario):** 🔴 BREACH at 09:20 — 3 tickets already
  breached (INC-1042 P1 checkout 500s, 50m over; INC-1050 P1 settlement
  file rejected, 5m over; INC-1047 P3 report export timeout, 20m over)
  and 2 at risk, the next breach INC-1043 (P2 CRM sync) in just 40
  minutes. Five tickets are on track and one is resolved and excluded, so
  the team chases 5 tickets instead of re-reading all 11.
- **What it shows:** SLA tracking and breach prevention, incident
  prioritisation, and escalating with a deadline and an owner instead of
  "some tickets might be late" (see the runbook).

## For Day 06 — Account Lockout Triage Tool
- **Situation:** Thursday morning, 09:20, the helpdesk phone rings — "I
  can't log in, it says my account is locked." The fix depends entirely
  on why: a locked account, an expired password, a broken authenticator
  and a disabled account all look the same to the caller, and guessing
  wrong wastes the call — or creates a security problem.
- **Action:** I wrote a Python tool that reads an account export and
  the login-attempt log and checks the likely causes in order for every
  user: disabled, locked, password expired, MFA failing after a correct
  password, 5+ failures in the last hour, password expiring within 7
  days, resolved (failure then success), or no attempts at all. It
  writes a one-page triage report with the evidence and the next step
  for each user, plus exit codes (0/1/2) a scheduler can act on. The
  tool never unlocks or resets anything — it tells the analyst what to
  do and who needs to do it.
- **Result (in the scenario):** 🔴 ADMIN ACTION NEEDED at 09:20 — 2
  users need the identity team: priya.k locked at 09:05 after 5 failed
  logins, 3 from the Mobile mail app (stale saved password, password
  itself valid until 2026-12-20), and chen.l disabled (do not
  re-enable). 3 more are helpdesk-fixable: sam.r's password expired
  yesterday, ana.m's password works but MFA failed 3 times in a row,
  and jordan.p's password expires in 3 days. alex.d already got in
  (typo) and mia.t has no login attempts at all — check the basics.
- **What it shows:** First-line support triage, identity and access
  basics (lockout vs expiry vs MFA vs disabled), verifying identity
  before any unlock, and escalating with evidence instead of "user
  can't log in" (see the runbook).

## For Day 07 — Error Code Knowledge Base
- **Situation:** Friday morning, 09:20, a user reports "checkout is
  failing with a timeout again." The fix for this error almost
  certainly exists in an old ticket — but nobody remembers the ticket
  number, so the analyst starts the investigation from zero while the
  checkout stays broken and the SLA clock runs.
- **Action:** I built a small searchable knowledge base (JSON, so any
  analyst can read and update it) of 12 past incidents — error code,
  system, symptom, cause, the fix that worked last time, the original
  ticket, and how many times the error has been seen. The Python tool
  searches by error code or by a word from the symptom, ranking an
  exact code match first, then a code substring, then keyword hits —
  and within each rank the fix seen most often comes first. It also
  lists entries by system and reports headline stats.
- **Result (in the scenario):** Searching `timeout` returns 3 matches
  in seconds. The top match is PAY-3002 — gateway timeout, seen 6
  times (INC-1048): check the vendor status page first and retry with
  back-off, never re-charge the customer twice. Next is DB-1045 —
  checkout database connection timeout, seen 5 times (INC-1042):
  the overnight batch held the connection pool open, so kill the idle
  batch sessions and restart the pool — don't restart the app first.
  Third is RPT-207 — monthly report timeout: add a date filter and
  schedule it off-peak. The base holds 12 entries across 8 systems,
  seen 44 times in total.
- **What it shows:** Knowledge management and triage thinking — search
  before you re-investigate, rank by what worked most often, verify
  the hit against the evidence before applying it, and write the new
  errors up after the fix so the next analyst finds them (see the
  runbook).

## For Day 08 — Duplicate Transaction Detector
- **Situation:** Finance reports the daily total looks too high, and a
  customer says they were charged twice for the same order. The extract
  has 22 transactions totalling $2,845.50 — but the re-posted rows are
  identical and the double-click pair has different transaction IDs, so
  a simple "find the repeated ID" check misses half the problem.
- **Action:** I loaded the extract into SQLite and ran duplicate-detection
  queries — exact duplicates with GROUP BY / HAVING on the transaction
  ID, and near duplicates with a self-join on customer + amount + day
  within a 10-minute window, so a double-click or a retry that got a new
  ID still shows up. Amounts are stored as integer cents so the totals
  are exact. The tool writes a one-page report naming every duplicate
  charge and the total amount at risk, and it also names the rows it
  deliberately did not flag.
- **Result (in the scenario):** 3 extra charges worth $208.73 — TXN-3001
  re-posted ($129.99), TXN-3005 re-posted ($18.75), and TXN-3004 /
  TXN-3010 charged twice 147 seconds apart (a double-click). The true
  day's value is $2,636.77 across 19 genuine charges. The tool did not
  flag TXN-3014 (same customer and amount, but 5 hours later — a
  legitimate repeat) or TXN-3017 (same amount, different customer).
- **What it shows:** SQL duplicate detection (GROUP BY / HAVING and
  self-joins), data validation with a time window, exact money handling,
  and escalating with named transactions and a refundable amount instead
  of "the total looks wrong" (see the runbook).

## For Day 09 — Database Lock / Slow Session Checker
- **Situation:** Users report the app is slow and checkouts are hanging —
  payments sit "processing" and never complete. The app servers look
  fine, so the next place to look is the database: is one session holding
  a lock that everyone else is waiting on?
- **Action:** I loaded a database session snapshot into SQLite and ran
  lock-analysis queries — blocking chains with a self-join on the
  blocking session, blocked sessions and their wait times, long-running
  active sessions over 10 minutes, idle-in-transaction sessions holding
  locks over 5 minutes, and a watch list for sessions in the 2–10 minute
  window. The tool only reads and reports — it never kills a session,
  because killing one rolls back real work and that call belongs to the
  DBA team.
- **Result (in the scenario):** 🔴 BLOCKING CHAIN in a 14-session
  snapshot — the overnight settlement batch (SESS-101) has been updating
  the transactions table for 42 minutes, blocking 3 sessions including a
  payment insert waiting 10m 40s, and a checkout session (SESS-102)
  updated an order 18 minutes ago then sat idle in its transaction,
  blocking the shipment update. A reporting query running 12 minutes is
  slow but blocks nobody, and two sessions sit on the watch list. The
  tool did not flag the session idle for 2 hours — plain idle holds no
  locks, so killing it would free nothing.
- **What it shows:** Database lock and blocking analysis, session triage
  (blocked vs blocker vs long-running vs idle), knowing what not to
  kill, and escalating to the DBA team with named session IDs instead of
  "the database is slow" (see the runbook).

## For Day 10 — Pre-Batch Data Validation Checker
- **Situation:** Monday, 09:20. The settlement batch is due to run at
  10:00 and Finance has just dropped the staging file — 20 rows. A bad
  row inside the batch means a failed run, a partial settlement and a
  10 a.m. incident, so the file has to be validated before the batch
  runs, not after it fails.
- **Action:** I loaded the staging CSV into SQLite and ran nine checks —
  duplicate transaction IDs, missing / negative / zero amounts,
  unexpected currency, future dates, malformed account numbers, missing
  customer IDs and invalid statuses. A row failing two rules still
  counts once, so the blocked count always adds up to the file total.
  The tool only reads and reports — it never edits the file or starts
  the batch, because deleting a row would lose a payment.
- **Result (in the scenario):** 🔴 BLOCKED — 10 of 20 rows fail, all 9
  rules firing once each, including TXN-4100 appearing twice (which
  would settle $129.99 twice) and a missing amount, a negative amount
  and a future-dated row. The 10 clean rows total $1,390.59 and are
  unaffected; the 10 bad rows go back to Finance by transaction ID,
  and the batch runs only after a corrected file re-validates clean.
- **What it shows:** Data validation before a batch run, SQL checks over
  a staging table, exit-code gating for a scheduler, and reporting bad
  rows by ID so the fixing team can act without a fresh investigation
  (see the runbook).

## For Day 11 — Reconciliation Summary Report Generator
- **Situation:** After the overnight settlement batch runs, Finance
  needs a daily reconciliation summary before the 10:00 close call —
  do the source system and the ledger agree? Comparing two files by
  hand is slow, and comparing only the totals hides the problem: a
  $5.00 under-posting and a $120.00 extra posting nearly cancel out.
- **Action:** I wrote a Python tool that matches both settlement
  files on transaction ID and classifies every transaction — matched
  exactly, amount mismatch, missing in ledger, missing in source —
  then totals each file with exact decimal arithmetic and writes a
  one-page summary with a verdict Finance can act on. It only reads
  and reports; fixing a break is Finance's call.
- **Result (in the scenario):** ⚠️ BREAKS FOUND — 16 of 19
  transactions match exactly, but 3 breaks worth $214.99 hide behind
  a net difference of only $25.01: TXN-5203 posted $5.00 short,
  TXN-5207 ($89.99) never reached the ledger, and TXN-5210 ($120.00)
  sits in the ledger with no source record. The day doesn't close
  until Finance clears all three by transaction ID.
- **What it shows:** Reconciliation thinking, not just totals —
  matching on IDs, classifying break types, exact decimal money
  maths, and reporting breaks so the fixing team can act without a
  fresh investigation (see the runbook).

## For Day 12 — Failed Batch Job Re-Run Checker
- **Situation:** The overnight settlement batch failed at 02:47,
  642 of 1,200 rows in, and Operations wants to re-run it before
  the business day starts. A blind re-run would post the 642 rows
  already settled a second time — and the job might still be
  running, have failed on a bad data row, or have a downstream job
  that already consumed the partial output.
- **Action:** I wrote a Python tool that runs six safety checks
  before anyone presses the button — previous run status, lock,
  failure cause classified from the log (transient vs data vs
  config), partial progress in rows and dollars, downstream jobs,
  and the input file's presence and checksum — then gives a
  verdict: safe to re-run (full or resume-and-skip), wait, or do
  not re-run with every blocker listed. It only reads and reports;
  it never re-runs the job or clears a lock.
- **Result (in the scenario):** 🟢 SAFE TO RE-RUN — resume, do not
  restart. The failure was a transient DB timeout, no lock is
  held, all three downstream jobs are still pending, and the input
  file is unchanged. The re-run starts from row 643 and skips the
  642 rows already posted (worth $156,594.61); afterwards 642 +
  558 must equal 1,200 with no transaction posted twice.
- **What it shows:** Batch operations judgement — checking
  re-run safety before the button press, classifying failure
  causes from logs, quantifying double-posting risk in dollars,
  and exit-code gating so a scheduler can block an unsafe re-run
  (see the runbook).

## For Day 13 — Service Health / Uptime Checker
- **Situation:** At the 09:20 morning health check, users started
  reporting stale data in the CRM — and nobody had looked at the
  probe log yet. "The CRM feels slow" could be a dead service, a
  slow dependency, or nothing at all, and guessing wrong means
  either escalating a non-incident or ignoring a real outage.
- **Action:** I wrote a Python tool that reads the service
  inventory (URL, expected status, latency threshold, uptime SLA,
  critical or not) and the last 24 hours of probe results — 1,728
  rows, one probe every 5 minutes per service — then reports
  per-service status (up, degraded, down, or unknown), uptime
  against SLA, average and p95 latency against threshold, and the
  outage detail: when the current failure run started, how long it
  has lasted, and the last error. It only reads and reports; it
  never restarts a service.
- **Result (in the scenario):** 🔴 CRITICAL — a critical service is
  DOWN. `crm-sync` failed 6 consecutive probes since 08:55 (25
  minutes, last error "Connection refused"), uptime 97.92% against
  a 99.5% SLA — the outage started 5 minutes before the first user
  call. `settlement-service` is DEGRADED: 100% uptime but averaging
  1,279 ms against an 800 ms threshold, so settlements run slow
  with nothing actually failed. The other four services are UP,
  including `payment-api`, which survived a single 03:20 timeout
  blip inside SLA.
- **What it shows:** Service monitoring and uptime reporting —
  separating down from degraded from healthy, reading latency
  (average and p95) as a health signal, not just up/down, and
  escalating with the outage start time, failure count, and last
  error so the platform team can act in 30 seconds (see the
  runbook).

## Rules I follow
- These are **portfolio practice scenarios with sample data** — I say that plainly.
- I never claim a tool, employer, or certification that isn't on my CV.
- The value is the *support process* around the code: verify, escalate, communicate, RCA.
