# Re-Run Safety Check — SETTLE_NIGHTLY

**Run checked:** 2026-11-17-0200 (started 2026-11-17 02:00:00, status FAILED, exit 3)

## Verdict: 🟢 SAFE TO RE-RUN — resume, do not restart

Re-run from row 643 and skip the 642 rows already posted (worth $156,594.61). A full re-run would post them a second time.

## Checks

- **Previous run status:** OK — run 2026-11-17-0200 FAILED at 2026-11-17 02:47:12 (exit 3, 642/1200 rows processed)
- **Lock:** OK — no lock held — previous run stopped
- **Failure cause:** OK — transient — log mentions 'timeout'
- **Partial progress:** RESUME REQUIRED — 642 rows already posted, worth $156,594.61 — a full re-run would post them again
- **Downstream jobs:** OK — 3 downstream job(s) still pending (LEDGER_POST, RECON_REPORT, FILE_EXPORT)
- **Input file:** OK — settlements_2026-11-17.csv present, checksum matches the failed run

## How to re-run (resume mode)

- Re-run with resume/skip-posted enabled, starting after row 642.
- Verify after the run: 1200 rows total, 642 from the failed run + 558 from the re-run, with no transaction posted twice.
- If the re-run fails again, do not keep retrying — stop and escalate with the new log.

This check only reads job history, logs and status files — it never re-runs the job, edits a file, or clears a lock.
