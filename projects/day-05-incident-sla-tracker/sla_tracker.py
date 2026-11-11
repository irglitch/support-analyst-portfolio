#!/usr/bin/env python3
"""
Day 05 — Incident SLA Tracker

Scenario: It is the 09:20 morning SLA review. Ten incidents are open and
nobody has checked the clock. Some are already past their resolution
deadline, others will breach within hours — and a breach nobody spotted
is the one the duty manager asks about first.

The tool reads an incident export (CSV), works out each open ticket's
resolution deadline from its priority's SLA target, and produces a
one-page report sorted by deadline: what is already BREACHED, what is
AT RISK, and what is ON TRACK — so support chases the right tickets
before the SLA clock runs out, not after.

CSV columns: ticket_id, summary, priority, status, assignee, created
  (created is ISO datetime, e.g. 2026-11-11T04:30)

Resolution SLA targets (hours from creation):
  P1: 4   P2: 8   P3: 24   P4: 48

A ticket is AT RISK when the time left is under 2 hours, or under 25%
of its SLA target — whichever is longer. Resolved/Closed tickets are
excluded from the breach math.

Usage:
  python3 sla_tracker.py sample_data/incidents.csv --out output/sla_report.md
  python3 sla_tracker.py sample_data/incidents.csv --now 2026-11-11T09:20 --out output/sla_report.md

Exit codes: 0 = all open tickets on track, 1 = at least one at risk,
2 = at least one breached. A scheduler can page on exit code 2.
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

SLA_TARGET_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
CLOSED_STATUSES = {"resolved", "closed", "cancelled"}
DEFAULT_NOW = "2026-11-11T09:20"


def parse_time(value):
    return datetime.fromisoformat(value.strip())


def fmt_delta(delta):
    """Human-readable '3h 20m' / '-50m' for a timedelta."""
    total_minutes = int(delta.total_seconds() // 60)
    sign = "-" if total_minutes < 0 else ""
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{sign}{hours}h {minutes}m"
    return f"{sign}{minutes}m"


def load_incidents(path):
    incidents = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            incidents.append({
                "ticket_id": row["ticket_id"].strip(),
                "summary": row["summary"].strip(),
                "priority": row["priority"].strip().upper(),
                "status": row["status"].strip(),
                "assignee": row["assignee"].strip(),
                "created": parse_time(row["created"]),
            })
    return incidents


def assess(incident, now):
    """Return (deadline, remaining, state) for one open incident."""
    target = SLA_TARGET_HOURS.get(incident["priority"])
    if target is None:
        return None, None, "UNKNOWN PRIORITY"
    deadline = incident["created"] + timedelta(hours=target)
    remaining = deadline - now
    if remaining.total_seconds() < 0:
        return deadline, remaining, "BREACHED"
    risk_window = max(timedelta(hours=2), timedelta(hours=target) * 0.25)
    if remaining <= risk_window:
        return deadline, remaining, "AT RISK"
    return deadline, remaining, "ON TRACK"


def analyse(incidents, now):
    """Split incidents into breached / at-risk / on-track / closed / unknown."""
    result = {"breached": [], "at_risk": [], "on_track": [],
              "closed": [], "unknown": []}
    for inc in incidents:
        if inc["status"].strip().lower() in CLOSED_STATUSES:
            result["closed"].append(inc)
            continue
        deadline, remaining, state = assess(inc, now)
        entry = {**inc, "deadline": deadline, "remaining": remaining}
        if state == "BREACHED":
            result["breached"].append(entry)
        elif state == "AT RISK":
            result["at_risk"].append(entry)
        elif state == "ON TRACK":
            result["on_track"].append(entry)
        else:
            result["unknown"].append(entry)
    for key in ("breached", "at_risk", "on_track"):
        result[key].sort(key=lambda e: e["deadline"])
    return result


def exit_code(result):
    if result["breached"]:
        return 2
    if result["at_risk"]:
        return 1
    return 0


def overall_status(result):
    if result["breached"]:
        return "🔴 BREACH — action now"
    if result["at_risk"]:
        return "🟠 AT RISK — act today"
    return "🟢 ALL ON TRACK"


def build_report(incidents, result, now, source_name):
    open_count = len(result["breached"]) + len(result["at_risk"]) + len(result["on_track"])
    lines = [
        "# Incident SLA Report",
        "",
        f"**Source:** `{source_name}`  ",
        f"**Checked at:** {now.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Overall status:** {overall_status(result)}  ",
        f"**Open tickets:** {open_count} · **Breached:** {len(result['breached'])} · "
        f"**At risk:** {len(result['at_risk'])} · **On track:** {len(result['on_track'])} · "
        f"**Resolved/closed (excluded):** {len(result['closed'])}",
        "",
        "## SLA targets (resolution)",
        "",
        "| Priority | Target |",
        "|---|---|",
    ]
    for prio, hours in SLA_TARGET_HOURS.items():
        lines.append(f"| {prio} | {hours}h |")
    lines += ["", "## All open tickets — sorted by deadline", "",
              "| Ticket | Priority | Summary | Assignee | Created | Deadline | Time left | Status |",
              "|---|---|---|---|---|---|---|---|"]
    for group, marker in (("breached", "🔴"), ("at_risk", "🟠"), ("on_track", "🟢")):
        for e in result[group]:
            lines.append(
                f"| {e['ticket_id']} | {e['priority']} | {e['summary']} | {e['assignee']} | "
                f"{e['created'].strftime('%Y-%m-%d %H:%M')} | "
                f"{e['deadline'].strftime('%Y-%m-%d %H:%M')} | {fmt_delta(e['remaining'])} | "
                f"{marker} {e['status']} |"
            )
    if result["unknown"]:
        lines += ["", "## ⚠️ Unknown priority — no SLA target, check manually", ""]
        for e in result["unknown"]:
            lines.append(f"- **{e['ticket_id']}** ({e['priority']}): {e['summary']} — assignee {e['assignee']}")
    lines += ["", "## What to do now", ""]
    if result["breached"]:
        lines.append("**🔴 BREACHED — escalate immediately:**")
        for e in result["breached"]:
            lines.append(
                f"- **{e['ticket_id']}** ({e['priority']}, {e['assignee']}): {e['summary']} — "
                f"breached {fmt_delta(-e['remaining'])} ago, deadline was "
                f"{e['deadline'].strftime('%Y-%m-%d %H:%M')}. Update the ticket, notify the "
                "duty manager, and record the breach reason."
            )
        lines.append("")
    if result["at_risk"]:
        lines.append("**🟠 AT RISK — act before the deadline:**")
        for e in result["at_risk"]:
            lines.append(
                f"- **{e['ticket_id']}** ({e['priority']}, {e['assignee']}): {e['summary']} — "
                f"only {fmt_delta(e['remaining'])} left, deadline "
                f"{e['deadline'].strftime('%Y-%m-%d %H:%M')}. Chase the assignee and check "
                "whether the fix or a workaround can land in time."
            )
        lines.append("")
    if not result["breached"] and not result["at_risk"]:
        lines.append("No breaches and nothing at risk — next check at the next SLA review.")
        lines.append("")
    lines += [
        "## Triage conclusion (auto-summary)",
        "",
    ]
    if result["breached"]:
        first = result["breached"][0]
        lines.append(
            f"{len(result['breached'])} ticket(s) already breached — the oldest is "
            f"**{first['ticket_id']}** ({first['priority']}, breached "
            f"{fmt_delta(-first['remaining'])} ago). "
            + (f"{len(result['at_risk'])} more breach within hours — "
               f"**{result['at_risk'][0]['ticket_id']}** first, in "
               f"{fmt_delta(result['at_risk'][0]['remaining'])}. " if result["at_risk"] else "")
            + "Start with the breaches: update, escalate, record the reason."
        )
    elif result["at_risk"]:
        first = result["at_risk"][0]
        lines.append(
            f"Nothing breached yet, but **{first['ticket_id']}** ({first['priority']}) "
            f"breaches in {fmt_delta(first['remaining'])} — chase it now, not at the "
            "next review."
        )
    else:
        lines.append("All open tickets are inside their SLA targets.")
    lines += ["", "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Incident SLA Tracker — spot breaches before they happen.")
    parser.add_argument("csv", help="Incident export CSV")
    parser.add_argument("--now", default=DEFAULT_NOW,
                        help="Check time as ISO datetime (default: %(default)s)")
    parser.add_argument("--out", help="Write the Markdown report to this file")
    args = parser.parse_args(argv)

    now = parse_time(args.now)
    incidents = load_incidents(args.csv)
    result = analyse(incidents, now)
    report = build_report(incidents, result, now, Path(args.csv).name)

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    print(f"Overall: {overall_status(result)} "
          f"({len(result['breached'])} breached, {len(result['at_risk'])} at risk, "
          f"{len(result['on_track'])} on track)")
    return exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
