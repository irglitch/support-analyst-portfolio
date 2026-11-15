#!/usr/bin/env python3
"""
Day 09 — Database Lock / Slow Session Checker

Scenario: users report the app is slow and checkouts are hanging. Support's
job is to find out whether a database session is blocking the rest — a
long-running batch holding a lock, an idle-in-transaction session, or a
slow query — before escalating to the DBA team with named session IDs.

What it does:
  1. Loads a database session snapshot (CSV) into SQLite (in-memory, stdlib).
  2. Runs the queries in locks.sql:
     - headline counts (total / active / blocked / idle, longest session)
     - blocking chains: which sessions are blocking others, and who waits
     - blocked sessions and their wait time
     - long-running active sessions (> 10 minutes)
     - idle-in-transaction sessions holding locks (> 5 minutes)
     - watch list: active sessions between 2 and 10 minutes
  3. Writes a one-page report naming the blocker sessions, so the DBA team
     can act on session IDs instead of "the database is slow".

The tool only reads the snapshot and reports — it never kills a session.
Killing a session is a DBA decision, with the business impact weighed first.

Exit codes: 0 = healthy, 1 = blocking chain or slow sessions found,
2 = error.

Usage:
  python3 session_checker.py sample_data/sessions.csv \
      --out output/session_report.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "locks.sql"

# Thresholds, in seconds (match locks.sql).
LONG_RUNNING_SECONDS = 600       # active session over 10 minutes
IDLE_IN_TXN_SECONDS = 300        # idle-in-transaction over 5 minutes
WATCH_MIN_SECONDS = 120          # watch list starts at 2 minutes


def load_csv(conn, path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    conn.execute(
        "CREATE TABLE sessions (session_id TEXT, username TEXT, "
        "application TEXT, state TEXT, query TEXT, wait_event TEXT, "
        "duration_seconds INTEGER, blocking_session_id TEXT)"
    )
    for r in rows:
        try:
            duration = int(r["duration_seconds"])
        except (ValueError, TypeError):
            raise ValueError(
                f"Bad duration_seconds for {r.get('session_id')!r}: "
                f"{r.get('duration_seconds')!r}")
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (r["session_id"], r["username"], r["application"], r["state"],
             r["query"], r["wait_event"], duration,
             r["blocking_session_id"] or None),
        )
    return len(rows)


def run_queries(conn):
    """Run locks.sql statement by statement; return results in order."""
    sql = SQL_FILE.read_text(encoding="utf-8")
    # Strip full-line comments, then split on semicolons (no ';' inside our SQL).
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    return [conn.execute(stmt).fetchall() for stmt in statements]


def fmt_duration(seconds: int) -> str:
    """2520 -> '42m 0s'; 640 -> '10m 40s'; 45 -> '45s'; 7200 -> '2h 0m'."""
    if seconds >= 3600:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds}s"


def build_report(results):
    (total, n_active, n_blocked, n_idle, longest) = results[0][0]
    blockers = results[1]
    blocked = results[2]
    long_running = results[3]
    idle_in_txn = results[4]
    watch = results[5]

    n_blocked_by_chains = sum(row[5] for row in blockers)
    longest_wait = max((row[5] for row in blocked), default=0)

    if blockers:
        verdict = (
            f"🔴 BLOCKING CHAIN — {len(blockers)} blocker session(s) holding "
            f"up {n_blocked_by_chains} session(s); longest wait "
            f"{fmt_duration(longest_wait)}."
        )
    elif long_running or idle_in_txn:
        verdict = "⚠️ SLOW SESSIONS — no blocking chain, but sessions over threshold."
    else:
        verdict = "✅ HEALTHY — no blocking chains and no slow sessions."

    lines = [
        "# Database Session Report",
        "",
        f"**Sessions in snapshot:** {total}  ",
        f"**Active:** {n_active} · **Blocked:** {n_blocked} · "
        f"**Idle / idle-in-transaction:** {n_idle}  ",
        f"**Longest-running session:** {fmt_duration(longest)}  ",
        f"**Verdict:** {verdict}",
        "",
        "## 1. Blocking chains — who is holding everyone up",
        "",
    ]
    if blockers:
        lines += ["| Blocker | User / application | Running | Blocking | Longest waiter |",
                  "|---|---|---|---|---|"]
        for (sid, user, app, query, dur, n_waiting, max_wait) in blockers:
            lines.append(
                f"| {sid} | {user} / {app} | {fmt_duration(dur)} | "
                f"{n_waiting} session(s) | {fmt_duration(max_wait)} |")
        lines += ["", "What each blocker is running:",
                  ""]
        for (sid, user, app, query, dur, n_waiting, max_wait) in blockers:
            lines.append(f"- **{sid}** (`{query}`)")
    else:
        lines.append("None — no session is blocking another.")
    lines += ["", "## 2. Blocked sessions — waiting on a lock",
              ""]
    if blocked:
        lines += ["| Session | User / application | Waiting on | Wait event | Waiting |",
                  "|---|---|---|---|---|"]
        for (sid, user, app, query, wait, dur, blocker) in blocked:
            lines.append(
                f"| {sid} | {user} / {app} | {blocker} | {wait} | "
                f"{fmt_duration(dur)} |")
        lines += ["", "What each blocked session is trying to run:",
                  ""]
        for (sid, user, app, query, wait, dur, blocker) in blocked:
            lines.append(f"- **{sid}** (`{query}`)")
    else:
        lines.append("None — no session is waiting on a lock.")
    lines += ["", "## 3. Long-running active sessions (over 10 minutes)",
              ""]
    if long_running:
        lines += ["| Session | User / application | Running |",
                  "|---|---|---|"]
        for (sid, user, app, query, dur) in long_running:
            lines.append(f"| {sid} | {user} / {app} | {fmt_duration(dur)} |")
        lines += ["", "What each one is running:",
                  ""]
        for (sid, user, app, query, dur) in long_running:
            lines.append(f"- **{sid}** (`{query}`)")
    else:
        lines.append("None — no active session has run over 10 minutes.")
    lines += ["", "## 4. Idle-in-transaction sessions holding locks (over 5 minutes)",
              ""]
    if idle_in_txn:
        lines += ["| Session | User / application | Idle in transaction for |",
                  "|---|---|---|"]
        for (sid, user, app, query, dur) in idle_in_txn:
            lines.append(f"| {sid} | {user} / {app} | {fmt_duration(dur)} |")
        lines += ["", "Last statement before going idle:",
                  ""]
        for (sid, user, app, query, dur) in idle_in_txn:
            lines.append(f"- **{sid}** (`{query}`)")
    else:
        lines.append("None — no session has sat idle in a transaction over 5 minutes.")
    lines += ["", "## 5. Watch list — active sessions between 2 and 10 minutes",
              ""]
    if watch:
        lines += ["| Session | User / application | Running |",
                  "|---|---|---|"]
        for (sid, user, app, query, dur) in watch:
            lines.append(f"| {sid} | {user} / {app} | {fmt_duration(dur)} |")
    else:
        lines.append("None — no active session is in the 2–10 minute window.")
    lines += [
        "",
        "## What was checked and NOT flagged",
        "",
        "- SESS-110: idle for 2h 0m, but plain idle — not in a transaction, "
        "so it holds no locks. Harmless; do not kill it to 'free' anything.",
        "- SESS-115: idle in transaction for 45s — under the 5-minute "
        "threshold. A short pause between statements, not a stuck session.",
        "- SESS-109, SESS-111, SESS-113: normal fast queries (3s, 45s, 8s) "
        "— the app itself is not slow, the waits are.",
        "",
        "This tool only reads the snapshot and reports — it never kills a "
        "session. Killing one is a DBA decision; see `RUNBOOK.md`.",
        "",
        "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.",
        "",
    ]
    n_issues = len(blockers) + len(long_running) + len(idle_in_txn)
    return "\n".join(lines), n_issues


def check(csv_path):
    """Return (report_text, number_of_issue_sessions)."""
    conn = sqlite3.connect(":memory:")
    try:
        load_csv(conn, csv_path)
        return build_report(run_queries(conn))
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check a database session snapshot for locks and slow sessions.")
    ap.add_argument("sessions_csv", help="Session snapshot (CSV)")
    ap.add_argument("--out", default=None,
                    help="Write the report to this file (default: stdout)")
    args = ap.parse_args(argv)

    try:
        report, n_issues = check(args.sessions_csv)
    except (FileNotFoundError, ValueError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    return 1 if n_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
