# RUNBOOK — Day 12: Failed Batch Job Re-Run Checker

## 1. Verify

- Run the tool and read the verdict first: 🟢 SAFE TO RE-RUN means
  go — but read *how* (full run vs resume-and-skip). 🟡 WAIT means
  the job is still running; 🔴 DO NOT RE-RUN means stop and clear
  the blockers.
- **Never re-run on "it failed" alone.** In the sample data the
  failed run already posted 642 rows worth $156,594.61. A full
  re-run would post every one of them a second time. The verdict
  is resume from row 643, not restart from row 1.
- Check the counts add up after the re-run: 642 from the failed
  run + 558 from the re-run = 1,200 total, with no transaction
  posted twice. If the post-run total is 1,842 rows, the re-run
  double-posted — escalate immediately.
- If the tool exits `2`, the inputs are the problem — a missing
  file or a bad row in one of the CSVs. Fix the file, don't
  hand-edit the report.
- Confirm the failure cause in the log yourself, don't take the
  classification on trust: "timeout" is retryable, "duplicate
  key" is not — the same exit code 3 can mean either.

## 2. Escalate (with facts)

- **Resume re-run (sample data):** tell Operations the exact
  instruction — "SETTLE_NIGHTLY run 2026-11-17-0200 failed at
  02:47 on a DB timeout after posting 642/1,200 rows. Safe to
  re-run as a resume from row 643, skipping the 642 already
  posted ($156,594.61). A full re-run would double-post them."
- **Data error:** escalate to the data owner with the log line —
  "the job failed on a duplicate key / bad amount, so a re-run
  will fail the same way until the row is fixed." Never re-run
  hoping a data error fixes itself.
- **Downstream already ran:** escalate to the downstream job's
  owner — "LEDGER_POST already consumed the partial output, so
  re-running changes its input." Re-running needs their agreement,
  not just Operations'.
- **Lock held:** escalate to the batch/platform team — the previous
  run may not have stopped cleanly, and clearing a lock by hand
  can orphan a running process.
- Escalate with the job ID, run ID, and the row counts — "642 of
  1,200 posted" gets a decision; "the batch failed" starts a fresh
  investigation.

## 3. Communicate

- Tell Operations the verdict and the mode in one message:
  "SETTLE_NIGHTLY is safe to re-run as a resume from row 643 —
  642 rows already posted ($156,594.61), so a full re-run would
  double-post. Downstream jobs haven't started yet."
- Tell the business the settlement is delayed but recoverable:
  "The overnight batch failed halfway on a database timeout.
  642 of 1,200 settlements posted; the remaining 558 go out on
  the resume run, and nothing is posted twice."
- Give a time, not a shrug: the safety check takes under a
  minute, and a resume run processes only the 558 unposted rows,
  so the settlement can still land before the morning close.

## 4. After recovery

- Re-run the checker on the new run and keep the report — the
  day's settlement is only confirmed when a run shows SUCCEEDED
  with 1,200/1,200 rows and the posted-transaction total matches
  the input file's total.
- Verify no transaction was posted twice: count distinct
  transaction IDs in the posted file. A duplicate is a Finance
  problem the same day, not a tomorrow problem.
- If the same job fails on a timeout again tomorrow, raise it as
  a platform issue: a batch that times out on the database two
  nights running is a capacity or connection-pool problem, not
  bad luck.
- File the report with the day's incident notes so the next
  overnight failure starts from the last known-good state, not
  from scratch.

## 5. RCA prompts

- Why did the database connection time out at 02:47 — was
  another job competing for the same pool, or is the timeout
  too short for the settlement volume?
- The job retried 3 times and failed 3 times — should the retry
  policy back off and alert sooner instead of burning 3 attempts
  in 3 seconds?
- Is there a resume/skip-posted mode in the scheduler already,
  or did this incident invent it? If it exists, why wasn't it
  the default re-run path?
- Should the re-run safety check run automatically when a batch
  fails, instead of waiting for the 09:20 manual check?
