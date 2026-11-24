#!/usr/bin/env python3
"""RCA Document Generator — Day 18 of the support analyst portfolio.

Scenario: INC-2011 (P1 — checkout returning HTTP 500s) is resolved, and
the duty manager needs the root-cause analysis document for the business
review within 24 hours. Until now an RCA meant copying the timeline out
of the ticket, re-typing the impact numbers from three different places
and hoping nothing was missed — and a review that finds a hole sends the
whole document back. This tool reads one incident file (JSON) and writes
a structured RCA document from a Markdown template: executive summary,
impact, timeline with durations, the 5-whys chain, root cause, action
items with owners and due dates, and a completeness check. A P1 RCA is
not FINAL until every required section is present — if anything is
missing the document is stamped DRAFT and the tool exits non-zero, so
an incomplete RCA can never be sent to the business by accident.

Usage:
    python3 rca_generator.py sample_data/incident.json
    python3 rca_generator.py sample_data/incident.json --out output/RCA-INC-2011.md
    python3 rca_generator.py sample_data/incident.json --template template.md

Exit codes:
    0  RCA complete — stamped FINAL
    1  RCA incomplete — stamped DRAFT, missing sections listed
    2  Input error (file missing, bad JSON, invalid incident record)

Python standard library only. The tool only reads the incident file and
writes the document — it never edits the ticket or the source systems.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Required fields per section. P1 incidents must have everything;
# P2/P3 may omit the 5-whys chain and the business-impact money figure.
REQUIRED_COMMON = ("incident_id", "title", "priority", "service",
                   "detected_at", "resolved_at", "root_cause",
                   "impact", "timeline", "action_items")
REQUIRED_P1 = ("five_whys", "business_impact", "evidence")
REQUIRED_ACTION = ("action", "owner", "due", "status")
TIMELINE_FIELDS = ("time", "event")

DEFAULT_TEMPLATE = """# Root Cause Analysis — {incident_id}: {title}

**Status:** {status} | **Priority:** {priority} | **Service:** {service}
**Detected:** {detected_at} | **Resolved:** {resolved_at} | **Duration:** {duration}
**Author:** {author} | **Generated:** {generated_at}

> {disclaimer}

## 1. Executive summary

{summary}

## 2. Impact

- **Users affected:** {users_affected}
- **Failed transactions:** {failed_transactions}
- **Business impact:** {business_impact}
- **Detection:** {detection}

## 3. Timeline (all times {timezone})

| Time | Elapsed | Event |
|---|---|---|
{timeline_rows}

## 4. Root cause

{root_cause}

## 5. Five whys

{five_whys}

## 6. What went well / what went badly

**Went well:**
{went_well}

**Went badly:**
{went_badly}

## 7. Action items

| # | Action | Owner | Due | Status |
|---|---|---|---|---|
{action_rows}

## 8. Evidence

{evidence}

## 9. Follow-up

{follow_up}
"""


def parse_time(value):
    """Parse an ISO timestamp; return None instead of raising."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def fmt_duration(total_minutes):
    if total_minutes is None:
        return "—"
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def check_completeness(incident):
    """Return a list of missing required sections/fields (empty = complete)."""
    missing = []
    for field in REQUIRED_COMMON:
        if not incident.get(field):
            missing.append(f"missing field: {field}")
    if str(incident.get("priority", "")).upper() == "P1":
        for field in REQUIRED_P1:
            if not incident.get(field):
                missing.append(f"missing P1 field: {field}")
    for i, item in enumerate(incident.get("action_items") or [], start=1):
        for field in REQUIRED_ACTION:
            if not item.get(field):
                missing.append(f"action item {i} missing field: {field}")
    for i, event in enumerate(incident.get("timeline") or [], start=1):
        for field in TIMELINE_FIELDS:
            if not event.get(field):
                missing.append(f"timeline event {i} missing field: {field}")
    whys = incident.get("five_whys") or []
    if whys and len(whys) < 3:
        missing.append("five_whys has fewer than 3 levels — chain is too shallow")
    impact = incident.get("impact") or {}
    for field in ("users_affected", "failed_transactions", "detection"):
        if field not in impact:
            missing.append(f"missing impact field: {field}")
    return missing


def build_timeline_rows(incident):
    detected = parse_time(incident.get("detected_at"))
    rows = []
    for event in incident.get("timeline") or []:
        when = parse_time(event.get("time"))
        elapsed = "—"
        if detected and when:
            delta_minutes = int((when - detected).total_seconds() // 60)
            # Events before detection (e.g. the change that caused the
            # incident) happened before the clock started — no elapsed time.
            elapsed = fmt_duration(delta_minutes) if delta_minutes >= 0 else "—"
        rows.append(f"| {event.get('time', '—')} | {elapsed} | {event.get('event', '—')} |")
    return "\n".join(rows) if rows else "| — | — | No timeline events recorded |"


def build_action_rows(incident):
    rows = []
    for i, item in enumerate(incident.get("action_items") or [], start=1):
        rows.append(f"| {i} | {item.get('action', '—')} | {item.get('owner', '—')} "
                    f"| {item.get('due', '—')} | {item.get('status', '—')} |")
    return "\n".join(rows) if rows else "| — | No action items recorded | — | — | — |"


def bullet_list(items, empty_text="Not recorded."):
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {item}" for item in items)


def numbered_whys(whys):
    if not whys:
        return "Not recorded."
    lines = []
    for i, why in enumerate(whys, start=1):
        lines.append(f"{i}. **Why?** {why}")
    return "\n".join(lines)


def render(incident, template, generated_at):
    """Render the RCA document. Returns (text, missing_sections)."""
    missing = check_completeness(incident)
    status = "DRAFT — incomplete, do not circulate" if missing else "FINAL"
    detected = parse_time(incident.get("detected_at"))
    resolved = parse_time(incident.get("resolved_at"))
    duration = None
    if detected and resolved:
        duration = int((resolved - detected).total_seconds() // 60)
    impact = incident.get("impact") or {}
    fields = {
        "incident_id": incident.get("incident_id", "UNKNOWN"),
        "title": incident.get("title", "Untitled incident"),
        "status": status,
        "priority": incident.get("priority", "—"),
        "service": incident.get("service", "—"),
        "detected_at": incident.get("detected_at", "—"),
        "resolved_at": incident.get("resolved_at", "—"),
        "duration": fmt_duration(duration),
        "author": incident.get("author", "Support team"),
        "generated_at": generated_at,
        "disclaimer": "Practice scenario with sample data, built for this "
                      "portfolio — not employer work.",
        "summary": incident.get("summary", "Not recorded."),
        "users_affected": impact.get("users_affected", "—"),
        "failed_transactions": impact.get("failed_transactions", "—"),
        "business_impact": incident.get("business_impact", "Not recorded."),
        "detection": impact.get("detection", "—"),
        "timezone": incident.get("timezone", "local time"),
        "timeline_rows": build_timeline_rows(incident),
        "root_cause": incident.get("root_cause", "Not recorded."),
        "five_whys": numbered_whys(incident.get("five_whys")),
        "went_well": bullet_list(incident.get("went_well")),
        "went_badly": bullet_list(incident.get("went_badly")),
        "action_rows": build_action_rows(incident),
        "evidence": bullet_list(incident.get("evidence")),
        "follow_up": incident.get("follow_up", "Not recorded."),
    }
    try:
        text = template.format(**fields)
    except KeyError as exc:
        raise ValueError(f"template uses unknown placeholder: {exc}") from exc
    if missing:
        checklist = "\n".join(f"- [ ] {item}" for item in missing)
        text += f"\n## Completeness checklist (must clear before FINAL)\n\n{checklist}\n"
    return text, missing


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an RCA document from an incident JSON file.")
    parser.add_argument("incident", type=Path, help="Incident JSON file (see sample_data/incident.json)")
    parser.add_argument("--template", type=Path, default=None,
                        help="Markdown template (default: built-in template)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output file (default: output/RCA-<incident_id>.md)")
    parser.add_argument("--generated-at", default=None,
                        help="Timestamp to stamp on the document (default: now)")
    args = parser.parse_args(argv)

    if not args.incident.is_file():
        print(f"ERROR: incident file not found: {args.incident}", file=sys.stderr)
        return 2
    try:
        incident = json.loads(args.incident.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: {args.incident} is not valid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(incident, dict) or not incident.get("incident_id"):
        print("ERROR: incident file must be a JSON object with an incident_id", file=sys.stderr)
        return 2

    template = DEFAULT_TEMPLATE
    if args.template:
        if not args.template.is_file():
            print(f"ERROR: template not found: {args.template}", file=sys.stderr)
            return 2
        template = args.template.read_text()

    generated_at = args.generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        text, missing = render(incident, template, generated_at)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    out = args.out or Path("output") / f"RCA-{incident['incident_id']}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    if missing:
        print(f"DRAFT: {incident['incident_id']} — {len(missing)} missing item(s):")
        for item in missing:
            print(f"  - {item}")
        print(f"Wrote {out} (DRAFT — do not circulate)")
        return 1
    print(f"FINAL: {incident['incident_id']} — RCA complete, wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
