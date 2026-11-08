#!/usr/bin/env python3
"""
Day 01 — Log Triage Analyzer

Scenario: Users report transactions stuck in "Pending". Support receives a
large application log and must answer, fast:
  1. Which service is actually failing?
  2. Which error is repeating, and when did it start?
  3. Is this a P1/P2 candidate, and who do we escalate to?

Log line format (sample data):
  2026-11-07T08:12:04Z [ERROR] [payment-api] [DB_CONN_TIMEOUT] message...

Usage:
  python3 log_triage.py sample_data/app.log --out output/incident_report.md
No external dependencies. Python 3.9+.
"""
import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

LINE_RE = re.compile(
    r"^(?P<ts>\S+)\s+\[(?P<level>TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\]\s+"
    r"\[(?P<service>[^\]]+)\]\s+\[(?P<code>[^\]]+)\]\s+(?P<msg>.*)$"
)

# Error codes that usually mean a shared dependency is down -> P1 candidate
P1_CODES = {"DB_CONN_TIMEOUT", "DB_CONN_REFUSED", "FILE_TRANSFER_DOWN", "OUT_OF_MEMORY"}
P2_CODES = {"FILE_NOT_FOUND", "UPSTREAM_5XX", "QUEUE_FULL"}


def parse_log(path):
    entries, unparsed = [], 0
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        m = LINE_RE.match(raw.strip())
        if not m:
            unparsed += 1
            continue
        entries.append(m.groupdict())
    return entries, unparsed


def suggest_priority(error_codes: Counter) -> tuple[str, str]:
    p1 = [c for c in error_codes if c in P1_CODES]
    if p1:
        return "P1 (candidate)", f"Dependency-failure error present: {', '.join(sorted(p1))}"
    p2 = [c for c in error_codes if c in P2_CODES]
    if p2:
        return "P2 (candidate)", f"Service-impacting error present: {', '.join(sorted(p2))}"
    if error_codes:
        return "P3 (candidate)", "Errors present but no known dependency-failure pattern"
    return "No incident", "No ERROR/FATAL lines found"


def build_report(entries, unparsed, source_name):
    levels = Counter(e["level"] for e in entries)
    errors = [e for e in entries if e["level"] in ("ERROR", "FATAL")]
    by_service = Counter(e["service"] for e in errors)
    by_code = Counter(e["code"] for e in errors)
    priority, reason = suggest_priority(by_code)

    first_seen, last_seen = {}, {}
    for e in errors:
        first_seen.setdefault(e["code"], e["ts"])
        last_seen[e["code"]] = e["ts"]

    top_service = by_service.most_common(1)[0][0] if by_service else "n/a"
    lines = [
        "# Incident Triage Report",
        "",
        f"**Source log:** `{source_name}`  ",
        f"**Lines parsed:** {len(entries)} · **Unparsed lines:** {unparsed}  ",
        f"**Errors (ERROR+FATAL):** {len(errors)}  ",
        f"**Suggested priority:** {priority} — {reason}  ",
        f"**Most affected service:** `{top_service}`",
        "",
        "## Counts by level",
        "",
        "| Level | Count |",
        "|---|---|",
    ]
    for lvl in ("FATAL", "ERROR", "WARN", "INFO", "DEBUG", "TRACE"):
        if levels.get(lvl):
            lines.append(f"| {lvl} | {levels[lvl]} |")

    lines += ["", "## Errors by service", "", "| Service | Errors |", "|---|---|"]
    for svc, n in by_service.most_common():
        lines.append(f"| {svc} | {n} |")

    lines += ["", "## Errors by code (first → last seen)", "",
              "| Error code | Count | First seen | Last seen |", "|---|---|---|---|"]
    for code, n in by_code.most_common():
        lines.append(f"| {code} | {n} | {first_seen[code]} | {last_seen[code]} |")

    lines += [
        "", "## Triage conclusion (auto-summary)",
        "",
    ]
    if by_code:
        top_code, top_n = by_code.most_common(1)[0]
        lines.append(
            f"The dominant failure is **{top_code}** ({top_n} occurrences, "
            f"{first_seen[top_code]} → {last_seen[top_code]}) on **{top_service}**. "
            "Start the investigation there, not with the user-facing symptom."
        )
    else:
        lines.append("No errors found. Check WARN trends and re-check with a wider time window.")
    lines += ["", "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.", ""]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Triage an application log into an incident summary.")
    ap.add_argument("logfile", help="Path to the application log")
    ap.add_argument("--out", default=None, help="Write the report to this file (default: stdout)")
    args = ap.parse_args(argv)

    entries, unparsed = parse_log(args.logfile)
    if not entries:
        print("No parseable log lines found — check the log format.", file=sys.stderr)
        return 1
    report = build_report(entries, unparsed, Path(args.logfile).name)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
