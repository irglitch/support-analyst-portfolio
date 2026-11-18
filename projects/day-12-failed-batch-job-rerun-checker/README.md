# Day 12 — Failed Batch Job Re-Run Checker

## 🧾 The situation (real-world use case)

**Wednesday, 09:20.** The overnight settlement batch (`SETTLE_NIGHTLY`)
failed at 02:47 with exit code 3, 642 of 1,200 rows in. Operations
wants to re-run it now, before the business day starts — and the
pressure is to just press the button. But a blind re-run is exactly
how double-postings happen: the 642 rows the failed run already
posted would be posted a second time, worth $156,594.61. And
re-running is wrong for other reasons too — the job might still be
running, it might have failed on a bad data row that will fail
again, or a downstream job might already have consumed the partial
output. The question before any re-run is not "did it fail?" but
"is it safe to run again, and if so, how?"

## 🔧 The fix

`rerun_checker.py` (Python stdlib only) runs six safety checks
against the job history, the failed run's log, the already-posted
transactions, the downstream jobs, and the job's status file:

1. **Previous run status** — a job that SUCCEEDED must never be
   re-run; a job still RUNNING means wait, not a second copy.
2. **Lock** — if the job still holds its lock, the previous run
   didn't stop cleanly.
3. **Failure cause**, classified from the log — *transient* (DB
   timeout, connection reset) is retryable; *data* (duplicate key,
   bad amount) will fail the same way until the row is fixed;
   *config* (permission denied, bad credentials) needs a fix
   first; *unknown* means find the cause before re-running blind.
4. **Partial progress** — how many rows were already posted and
   what they're worth, so a full re-run's double-posting cost is
   visible in dollars, not just row counts.
5. **Downstream jobs** — if one already ran on the partial output,
   re-running changes what it consumed.
6. **Input file** — still present, and checksum unchanged since
   the failed run started.

The verdict is 🟢 **SAFE TO RE-RUN** (full, or resume-and-skip),
🟡 **WAIT**, or 🔴 **DO NOT RE-RUN** with every blocker listed.
The tool only reads and reports — it never re-runs the job, never
edits a file, and never clears a lock. Re-running is Operations'
call; support supplies the evidence.

## ▶️ Run it

```bash
cd projects/day-12-failed-batch-job-rerun-checker
python3 rerun_checker.py --job SETTLE_NIGHTLY sample_data/job_history.csv sample_data/job_log.txt sample_data/posted_transactions.csv sample_data/downstream_jobs.csv sample_data/job_status.json --out output/rerun_check.md
cat output/rerun_check.md
```

Exit codes: `0` = SAFE TO RE-RUN, `1` = DO NOT RE-RUN / WAIT,
`2` = error.

**Result on the sample data:** 🟢 **SAFE TO RE-RUN — resume, do not
restart.** Run `2026-11-17-0200` failed at 02:47 on a transient DB
connection timeout (exit 3) after posting 642 of 1,200 rows. No lock
is held, all three downstream jobs (LEDGER_POST, RECON_REPORT,
FILE_EXPORT) are still pending, and the input file is present with a
matching checksum. The re-run must start from row 643 and skip the
642 rows already posted — worth $156,594.61 — because a full re-run
would post them a second time. After the re-run, the totals must
reconcile: 642 from the failed run + 558 from the re-run = 1,200,
with no transaction posted twice.

## ✅ Tests

20 unittest tests, all passing — from the project folder and from the
repo root:

```bash
python3 -m unittest discover -s tests
# Ran 20 tests in 0.016s — OK
```

Tests cover: the sample-data verdict (safe resume, 642 posted rows,
$156,594.61), failure-cause classification (transient / data /
config / unknown), and every blocker — already-succeeded job,
still-running job, lock held, data error, downstream job already
ran, missing or changed input file, unknown cause — plus the
no-rows-posted full re-run case, the report naming the resume row,
and the CLI exit codes (0 / 1 / 2).

## 🛠 Skills demonstrated

- Batch operations judgement: re-run safety before the button press
- Failure-cause classification from logs (transient vs data vs config)
- Partial-completion and double-posting risk in dollars, not just rows
- Downstream-dependency awareness before restarting a job
- Exit-code gating so a scheduler can block an unsafe re-run

Practice scenario with sample data, built for this portfolio — not employer work.
