#!/usr/bin/env python3
"""
Day 12 — Failed Batch Job Re-Run Checker

Scenario: Wednesday, 09:20. The overnight settlement batch
(SETTLE_NIGHTLY) failed at 02:47 with exit code 3, partway through its
run. Operations wants to re-run it now, before the business day
starts. A blind re-run is how double-postings happen: rows the failed
run already posted would be posted again, a downstream job may already
have consumed the partial output, or the job may have failed on a bad
data row that will fail again. This tool answers one question before
anyone presses the button — is it safe to re-run, and if so, how?

What it checks, in order:
  1. Previous run status — a job that SUCCEEDED must never be
     re-run, and a job still RUNNING must be left alone.
  2. Lock — if the job still holds its lock, something is still
     running or a previous run died uncleanly.
  3. Failure cause, classified from the job log:
     transient (DB timeout, connection reset) — retryable;
     data error (duplicate key, bad amount, invalid row) — the
     re-run will fail the same way until the data is fixed;
     config error (missing config, bad credentials) — needs a fix
     first, not a retry.
  4. Partial progress — how many rows the failed run already
     posted, and what they are worth. A full re-run would post
     them again, so a safe re-run must resume and skip them.
  5. Downstream jobs — if a downstream job already ran on the
     partial output, re-running changes what it consumed.
  6. Input file — still present, and checksum unchanged since the
     failed run started.

Verdict: SAFE TO RE-RUN (full, or resume-and-skip-posted),
DO NOT RE-RUN (blockers listed), or WAIT (job still running).

The tool only reads and reports — it never re-runs the job, never
edits a file, and never clears a lock. Re-running is Operations'
call; support supplies the evidence.

Exit codes: 0 = SAFE TO RE-RUN, 1 = DO NOT RE-RUN / WAIT,
2 = error (file missing / unreadable / wrong shape).

Usage:
  python3 rerun_checker.py --job SETTLE_NIGHTLY \\
      sample_data/job_history.csv sample_data/job_log.txt \\
      sample_data/posted_transactions.csv sample_data/downstream_jobs.csv \\
      sample_data/job_status.json --out output/rerun_check.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Failure-cause keywords, checked against the job log (lowercase).
TRANSIENT_KEYWORDS = (
    "timeout", "connection reset", "connection refused",
    "temporarily unavailable", "deadlock", "out of memory",
)
DATA_KEYWORDS = (
    "duplicate key", "duplicate txn", "invalid amount", "bad amount",
    "missing amount", "constraint violation", "invalid row",
    "parse error", "malformed",
)
CONFIG_KEYWORDS = (
    "config not found", "missing config", "invalid credentials",
    "permission denied", "authentication failed", "unknown host",
)


def load_history(path, job_id):
    """Load job runs for one job, newest first. Raises ValueError."""
    runs = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            required = {"job_id", "run_id", "started_at", "status",
                        "rows_processed", "rows_total"}
            if reader.fieldnames is None or not required <= set(reader.fieldnames):
                raise ValueError(f"{path}: expected columns {sorted(required)}")
            for line_no, row in enumerate(reader, start=2):
                if (row.get("job_id") or "").strip() != job_id:
                    continue
                try:
                    processed = int((row.get("rows_processed") or "").strip())
                    total = int((row.get("rows_total") or "").strip())
                except ValueError:
                    raise ValueError(
                        f"{path} line {line_no}: bad row counts for "
                        f"{row.get('run_id')}")
                runs.append({
                    "run_id": (row.get("run_id") or "").strip(),
                    "started_at": (row.get("started_at") or "").strip(),
                    "ended_at": (row.get("ended_at") or "").strip(),
                    "status": (row.get("status") or "").strip().upper(),
                    "exit_code": (row.get("exit_code") or "").strip(),
                    "rows_processed": processed,
                    "rows_total": total,
                    "failure_reason": (row.get("failure_reason") or "").strip(),
                })
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}")
    if not runs:
        raise ValueError(f"{path}: no runs found for job {job_id}")
    return runs


def classify_failure(log_text):
    """Classify the failure cause from the job log. Returns a
    (cause, detail) pair: cause is 'transient', 'data', 'config',
    or 'unknown'."""
    text = log_text.lower()
    for keyword in DATA_KEYWORDS:
        if keyword in text:
            return "data", f"log mentions '{keyword}'"
    for keyword in CONFIG_KEYWORDS:
        if keyword in text:
            return "config", f"log mentions '{keyword}'"
    for keyword in TRANSIENT_KEYWORDS:
        if keyword in text:
            return "transient", f"log mentions '{keyword}'"
    return "unknown", "no recognised failure cause in the log"


def load_posted(path):
    """Load transactions already posted by the failed run.
    Returns (count, total Decimal). Raises ValueError."""
    count = 0
    total = Decimal("0")
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or "txn_id" not in reader.fieldnames \
                    or "amount" not in reader.fieldnames:
                raise ValueError(f"{path}: expected columns txn_id, amount, ...")
            for line_no, row in enumerate(reader, start=2):
                txn_id = (row.get("txn_id") or "").strip()
                if not txn_id:
                    raise ValueError(f"{path} line {line_no}: missing txn_id")
                try:
                    amount = Decimal((row.get("amount") or "").strip())
                except InvalidOperation:
                    raise ValueError(
                        f"{path} line {line_no}: bad amount "
                        f"'{row.get('amount')}' for {txn_id}")
                count += 1
                total += amount
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}")
    return count, total


def load_downstream(path, job_id):
    """Load downstream jobs for one job. Raises ValueError."""
    jobs = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            required = {"job_id", "depends_on", "status"}
            if reader.fieldnames is None or not required <= set(reader.fieldnames):
                raise ValueError(f"{path}: expected columns {sorted(required)}")
            for row in reader:
                if (row.get("depends_on") or "").strip() != job_id:
                    continue
                jobs.append({
                    "job_id": (row.get("job_id") or "").strip(),
                    "status": (row.get("status") or "").strip().upper(),
                    "started_at": (row.get("started_at") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                })
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}")
    return jobs


def load_status(path):
    """Load the job status file (lock + input file state). Raises ValueError."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON — {exc}")
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def check_rerun(job_id, runs, log_text, posted_count, posted_total,
                downstream, status):
    """Run every safety check. Returns a dict with verdict, blockers
    and the evidence behind them."""
    latest = runs[0]
    checks = []   # (name, result, detail)
    blockers = []

    # 1. Previous run status
    if latest["status"] == "RUNNING":
        checks.append(("Previous run status",
                       "WAIT",
                       f"run {latest['run_id']} started "
                       f"{latest['started_at']} is still RUNNING"))
        blockers.append("Job is still running — do not start a second copy.")
        return {"verdict": "WAIT", "checks": checks, "blockers": blockers,
                "latest": latest, "cause": None, "cause_detail": None,
                "posted_count": posted_count, "posted_total": posted_total,
                "downstream": downstream, "resume": False}
    if latest["status"] == "SUCCEEDED":
        checks.append(("Previous run status",
                       "BLOCKED",
                       f"run {latest['run_id']} already SUCCEEDED "
                       f"({latest['rows_processed']}/{latest['rows_total']} rows)"))
        blockers.append("Job already succeeded — re-running would "
                        "re-post every row.")
    elif latest["status"] == "FAILED":
        checks.append(("Previous run status",
                       "OK",
                       f"run {latest['run_id']} FAILED at "
                       f"{latest['ended_at'] or latest['started_at']} "
                       f"(exit {latest['exit_code'] or '?'}, "
                       f"{latest['rows_processed']}/{latest['rows_total']} "
                       f"rows processed)"))
    else:
        checks.append(("Previous run status",
                       "BLOCKED",
                       f"run {latest['run_id']} has unexpected status "
                       f"'{latest['status']}'"))
        blockers.append(f"Unexpected run status '{latest['status']}' — "
                        "confirm the job state before re-running.")

    # 2. Lock
    if status.get("lock_held"):
        holder = status.get("lock_holder") or "unknown holder"
        checks.append(("Lock", "BLOCKED", f"lock still held by {holder}"))
        blockers.append(f"Job lock still held ({holder}) — the previous "
                        "run may not have stopped cleanly.")
    else:
        checks.append(("Lock", "OK", "no lock held — previous run stopped"))

    # 3. Failure cause
    cause, cause_detail = classify_failure(log_text)
    if cause == "transient":
        checks.append(("Failure cause", "OK",
                       f"transient — {cause_detail}"))
    elif cause == "data":
        checks.append(("Failure cause", "BLOCKED",
                       f"data error — {cause_detail}"))
        blockers.append("Failure was a data error — a re-run will fail "
                        "the same way until the bad row is fixed.")
    elif cause == "config":
        checks.append(("Failure cause", "BLOCKED",
                       f"config error — {cause_detail}"))
        blockers.append("Failure was a config error — fix the config "
                        "before re-running.")
    else:
        checks.append(("Failure cause", "BLOCKED",
                       "unknown — no recognised failure cause in the log"))
        blockers.append("Failure cause unknown — find it in the log "
                        "before re-running blind.")

    # 4. Partial progress — what a full re-run would double-post
    if posted_count > 0:
        checks.append(("Partial progress", "RESUME REQUIRED",
                       f"{posted_count} rows already posted, worth "
                       f"${posted_total:,.2f} — a full re-run would "
                       f"post them again"))
    else:
        checks.append(("Partial progress", "OK",
                       "no rows posted — a full re-run is safe on this count"))

    # 5. Downstream jobs
    consumed = [j for j in downstream if j["status"] in ("COMPLETED", "RUNNING")]
    if consumed:
        names = ", ".join(j["job_id"] for j in consumed)
        checks.append(("Downstream jobs", "BLOCKED",
                       f"{names} already ran on the partial output"))
        blockers.append(f"Downstream job(s) {names} already ran on the "
                        "partial output — re-running changes what they "
                        "consumed; coordinate with their owners first.")
    else:
        pending = [j["job_id"] for j in downstream if j["status"] == "PENDING"]
        checks.append(("Downstream jobs", "OK",
                       f"{len(pending)} downstream job(s) still pending "
                       f"({', '.join(pending) if pending else 'none listed'})"))

    # 6. Input file
    if not status.get("input_file_present"):
        checks.append(("Input file", "BLOCKED",
                       f"{status.get('input_file') or 'input file'} is missing"))
        blockers.append("Input file is missing — the re-run has nothing "
                        "to process.")
    elif not status.get("input_checksum_match"):
        checks.append(("Input file", "BLOCKED",
                       "input file changed since the failed run started"))
        blockers.append("Input file changed since the failed run — "
                        "confirm which version is the right one first.")
    else:
        checks.append(("Input file", "OK",
                       f"{status.get('input_file') or 'input file'} present, "
                       "checksum matches the failed run"))

    verdict = "DO NOT RE-RUN" if blockers else "SAFE TO RE-RUN"
    resume = (verdict == "SAFE TO RE-RUN" and posted_count > 0)
    return {"verdict": verdict, "checks": checks, "blockers": blockers,
            "latest": latest, "cause": cause, "cause_detail": cause_detail,
            "posted_count": posted_count, "posted_total": posted_total,
            "downstream": downstream, "resume": resume}


def render_report(result, job_id):
    latest = result["latest"]
    lines = [
        f"# Re-Run Safety Check — {job_id}",
        "",
        f"**Run checked:** {latest['run_id']} "
        f"(started {latest['started_at']}, status {latest['status']}, "
        f"exit {latest['exit_code'] or '?'})",
        "",
    ]
    verdict = result["verdict"]
    if verdict == "SAFE TO RE-RUN":
        if result["resume"]:
            lines.append("## Verdict: 🟢 SAFE TO RE-RUN — resume, do not restart")
            lines.append("")
            lines.append(f"Re-run from row {result['posted_count'] + 1} and "
                         f"skip the {result['posted_count']} rows already "
                         f"posted (worth "
                         f"${result['posted_total']:,.2f}). A full re-run "
                         "would post them a second time.")
        else:
            lines.append("## Verdict: 🟢 SAFE TO RE-RUN — full run")
            lines.append("")
            lines.append("No rows were posted by the failed run, so a full "
                         "re-run is safe.")
    elif verdict == "WAIT":
        lines.append("## Verdict: 🟡 WAIT — job is still running")
        lines.append("")
        lines.append("Do not start a second copy. Wait for the running "
                     "job to finish or fail, then check again.")
    else:
        lines.append("## Verdict: 🔴 DO NOT RE-RUN")
        lines.append("")
        lines.append("Blockers found — re-running now would make things "
                     "worse. Clear every blocker below first.")
    lines += ["", "## Checks", ""]
    for name, outcome, detail in result["checks"]:
        lines.append(f"- **{name}:** {outcome} — {detail}")
    if result["blockers"]:
        lines += ["", "## Blockers", ""]
        for blocker in result["blockers"]:
            lines.append(f"- {blocker}")
    if result["resume"]:
        lines += [
            "",
            "## How to re-run (resume mode)",
            "",
            f"- Re-run with resume/skip-posted enabled, starting after "
            f"row {result['posted_count']}.",
            f"- Verify after the run: {latest['rows_total']} rows total, "
            f"{result['posted_count']} from the failed run + "
            f"{latest['rows_total'] - result['posted_count']} from the "
            f"re-run, with no transaction posted twice.",
            "- If the re-run fails again, do not keep retrying — stop "
            "and escalate with the new log.",
        ]
    lines += [
        "",
        "This check only reads job history, logs and status files — it "
        "never re-runs the job, edits a file, or clears a lock.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check whether a failed batch job is safe to re-run.")
    parser.add_argument("--job", required=True, help="job id to check")
    parser.add_argument("history", help="job history CSV")
    parser.add_argument("log", help="failed run log file")
    parser.add_argument("posted", help="transactions already posted CSV")
    parser.add_argument("downstream", help="downstream jobs CSV")
    parser.add_argument("status", help="job status JSON (lock + input file)")
    parser.add_argument("--out", help="write the report to this file")
    args = parser.parse_args(argv)

    try:
        runs = load_history(args.history, args.job)
        log_text = Path(args.log).read_text(encoding="utf-8")
        posted_count, posted_total = load_posted(args.posted)
        downstream = load_downstream(args.downstream, args.job)
        status = load_status(args.status)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    result = check_rerun(args.job, runs, log_text, posted_count,
                         posted_total, downstream, status)
    report = render_report(result, args.job)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if result["verdict"] == "SAFE TO RE-RUN" else 1


if __name__ == "__main__":
    sys.exit(main())
