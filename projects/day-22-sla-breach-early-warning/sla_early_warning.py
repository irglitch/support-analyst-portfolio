#!/usr/bin/env python3
"""SLA Breach Early Warning — Day 22 of the support analyst portfolio.

Scenario: Saturday 09:20, the weekend on-call check. Day 05's tracker
answers "what has breached?" — by then the SLA is already lost. This
tool answers the earlier question: "what will breach if nothing
changes, and what is quietly going stale?" A P1 with 20 minutes left
on the clock but 90 minutes of work remaining will breach, however
green its deadline maths looks at a glance. An unassigned ticket and
a ticket with no update since yesterday are breaches in slow motion.

For each open ticket the tool forecasts a finish time (now + the
assignee's estimated remaining work), compares it with the SLA
deadline, and layers on the early-warning signals: no recent update,
unassigned aging, blocked-on-vendor time, and an assignee carrying
several at-risk tickets at once. Every warning names the action it
calls for — escalate, chase, reassign, or update — while there is
still time for the action to matter.

Exit codes: 0 = nothing needs action, 1 = warnings (will-breach
forecasts, stale, unassigned, or blocked tickets), 2 = at least one
ticket already breached, or an input error.

Usage:
  python3 sla_early_warning.py sample_data/open_tickets.json
  python3 sla_early_warning.py sample_data/open_tickets.json \\
      --out output/sla_early_warning_report.md
  python3 sla_early_warning.py sample_data/open_tickets.json \\
      --now 2026-11-28T11:00 --out output/sla_early_warning_report.md

Python standard library only. The tool only reads and warns — it
never edits, reassigns, or closes a ticket.
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SLA_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
# Minutes without an update before a ticket counts as going stale.
STALE_MINUTES = {"P1": 30, "P2": 60, "P3": 240, "P4": 480}
CLOSED_STATUSES = {"resolved", "closed", "cancelled", "canceled"}
# An assignee holding this many warned tickets at once is a risk too.
OVERLOAD_THRESHOLD = 3


def parse_time(value):
    return datetime.fromisoformat(value)


def fmt_minutes(minutes):
    minutes = int(round(abs(minutes)))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins:02d}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def deadline_for(ticket):
    return parse_time(ticket["created"]) + timedelta(
        hours=SLA_HOURS[ticket["priority"]])


def forecast_finish(ticket, now):
    return now + timedelta(
        minutes=ticket.get("estimated_remaining_minutes") or 0)


def assess(ticket, now):
    """Return a dict of warning facts for one open ticket."""
    deadline = deadline_for(ticket)
    finish = forecast_finish(ticket, now)
    minutes_left = (deadline - now).total_seconds() / 60
    forecast_overrun = (finish - deadline).total_seconds() / 60
    last_update = parse_time(ticket["last_update"])
    stale_for = (now - last_update).total_seconds() / 60
    age = (now - parse_time(ticket["created"])).total_seconds() / 60

    warnings = []
    if minutes_left < 0:
        level = "BREACHED"
        warnings.append(
            f"breached {fmt_minutes(minutes_left)} ago — the forecast "
            f"no longer matters, recovery and communication do")
    elif forecast_overrun > 0:
        level = "WILL BREACH"
        warnings.append(
            f"forecast finish {finish:%H:%M} is "
            f"{fmt_minutes(forecast_overrun)} past the "
            f"{deadline:%H:%M} deadline — it breaches on current "
            f"pace, with {fmt_minutes(minutes_left)} of clock left")
    else:
        level = "ON TRACK"

    if stale_for > STALE_MINUTES[ticket["priority"]]:
        warnings.append(
            f"no update for {fmt_minutes(stale_for)} "
            f"(threshold {fmt_minutes(STALE_MINUTES[ticket['priority']])} "
            f"for {ticket['priority']}) — the estimate may be fiction")
        if level == "ON TRACK":
            level = "AT RISK"
    if not ticket.get("assignee"):
        warnings.append(
            f"unassigned for {fmt_minutes(age)} — nobody owns the "
            f"deadline")
        if level == "ON TRACK":
            level = "AT RISK"
    if ticket.get("blocked_on"):
        warnings.append(
            f"blocked on {ticket['blocked_on']} — chase the blocker, "
            f"not the assignee")
        if level == "ON TRACK":
            level = "AT RISK"

    actions = {
        "BREACHED": "Escalate now: duty manager, recovery plan, "
                    "business update with the breach stated plainly",
        "WILL BREACH": "Act while it can still be saved: add help, "
                       "cut scope, or escalate before the deadline",
        "AT RISK": "Chase today: get an update, an owner, or the "
                   "blocker moving",
        "ON TRACK": "No action — re-check at the next sweep",
    }
    return {
        "ticket": ticket, "deadline": deadline, "finish": finish,
        "minutes_left": minutes_left, "level": level,
        "warnings": warnings, "action": actions[level],
    }


def assess_all(tickets, now):
    open_tickets = [t for t in tickets
                    if t.get("status", "").lower() not in CLOSED_STATUSES]
    closed = [t for t in tickets if t not in open_tickets]
    results = [assess(t, now) for t in open_tickets]
    order = {"BREACHED": 0, "WILL BREACH": 1, "AT RISK": 2, "ON TRACK": 3}
    results.sort(key=lambda r: (order[r["level"]], r["deadline"]))
    warned = Counter(r["ticket"]["assignee"] for r in results
                     if r["level"] != "ON TRACK" and r["ticket"].get("assignee"))
    overloaded = {name: n for name, n in warned.items()
                  if n >= OVERLOAD_THRESHOLD}
    return results, closed, overloaded


def render(results, closed, overloaded, now):
    counts = Counter(r["level"] for r in results)
    breached = counts.get("BREACHED", 0)
    will = counts.get("WILL BREACH", 0)
    at_risk = counts.get("AT RISK", 0)
    on_track = counts.get("ON TRACK", 0)
    if breached:
        headline = (f"🔴 BREACH — {breached} already breached, "
                    f"{will} forecast to breach, {at_risk} at risk")
    elif will or at_risk:
        headline = (f"🟠 EARLY WARNING — {will} forecast to breach, "
                    f"{at_risk} at risk, none breached yet")
    else:
        headline = "🟢 ALL ON TRACK — no breach forecast"

    lines = [
        "# SLA Breach Early Warning Report",
        "",
        f"Checked at: {now:%Y-%m-%d %H:%M} · "
        f"{len(results)} open tickets · {len(closed)} closed/resolved excluded",
        "",
        f"**{headline}**",
        "",
        f"Breached: {breached} · Will breach (forecast): {will} · "
        f"At risk: {at_risk} · On track: {on_track}",
        "",
    ]
    icons = {"BREACHED": "🔴", "WILL BREACH": "🟠", "AT RISK": "🟡",
             "ON TRACK": "🟢"}
    for r in results:
        t = r["ticket"]
        lines.append(
            f"## {icons[r['level']]} {t['ticket_id']} — {r['level']} "
            f"({t['priority']}, {t.get('assignee') or 'UNASSIGNED'})")
        lines.append(f"- {t['summary']}")
        lines.append(
            f"- Deadline {r['deadline']:%Y-%m-%d %H:%M} · "
            f"forecast finish {r['finish']:%H:%M} · "
            f"progress {t.get('progress_percent', 0)}% · "
            f"est. remaining {fmt_minutes(t.get('estimated_remaining_minutes') or 0)}")
        for warning in r["warnings"]:
            lines.append(f"- ⚠️ {warning}")
        lines.append(f"- **Action:** {r['action']}")
        lines.append("")
    if overloaded:
        lines.append("## ⚠️ Assignee overload")
        for name, n in sorted(overloaded.items()):
            lines.append(
                f"- {name} holds {n} warned tickets — rebalancing one "
                f"is itself a breach-prevention action")
        lines.append("")
    lines.append(
        "*Practice scenario with sample data, built for this "
        "portfolio — not employer work.*")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", help="JSON file of open tickets")
    parser.add_argument("--out", help="write the report to this file")
    parser.add_argument("--now", help="check time, e.g. 2026-11-28T09:20 "
                        "(default: the file's checked_at, else now)")
    args = parser.parse_args(argv)

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        tickets = data["tickets"]
        now = parse_time(args.now or data.get("checked_at")
                         or datetime.now().isoformat(timespec="minutes"))
        results, closed, overloaded = assess_all(tickets, now)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: cannot assess {args.input}: {exc}", file=sys.stderr)
        return 2

    report = render(results, closed, overloaded, now)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
    print(report)

    levels = {r["level"] for r in results}
    if "BREACHED" in levels:
        return 2
    if levels & {"WILL BREACH", "AT RISK"}:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
