#!/usr/bin/env python3
"""Change Request Readiness Checker — Day 19 of the support analyst portfolio.

Scenario: Wednesday 09:20, the change manager asks support to review
tomorrow's changes before CAB. The lesson of INC-2011 (Day 18) is fresh:
CHG-8841 cut a database connection pool 200 -> 50 with no load test and
no rollback trigger, and checkout was down for 1h 45m. Reviewing five
change requests by hand means re-reading every field of every ticket —
and the missing rollback trigger is exactly the field that gets skimmed.

This tool reads the change requests (JSON) and runs the readiness checks
support applies before a change is approved: description and impact,
test evidence (including the load-test rule for high-risk and
limit-changing changes), a rollback plan with a trigger and enough
window left to use it, approvals (including separation of duties),
communications, dependencies, and post-implementation verification.
Each change gets a verdict — READY, READY WITH CONDITIONS, or NOT
READY — with every blocker and warning named, and the report ends with
a ranked action list CAB can work through.

Exit codes: 0 = every change READY, 1 = conditions or blockers found
(CAB action needed), 2 = error (file missing / unreadable / wrong shape).

Usage:
  python3 change_readiness.py sample_data/change_requests.json
  python3 change_readiness.py sample_data/change_requests.json \\
      --out output/change_readiness_report.md --generated-at "2026-11-25 09:20"
  python3 change_readiness.py sample_data/change_requests.json --change CHG-8901

Python standard library only. The tool only reads and reports — it never
approves, schedules, or implements a change; those calls belong to CAB.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

VALID_RISKS = ("low", "medium", "high")
# A rollback trigger written as one of these is not a trigger.
PLACEHOLDER_TRIGGERS = {"", "tbd", "n/a", "none", "tbc", "-"}
# If implementation + rollback would consume more than this share of the
# window, the change fits but with no room for trouble — a warning.
TIGHT_WINDOW_SHARE = 0.8
MIN_DESCRIPTION_CHARS = 20


def parse_time(value):
    """Parse an ISO timestamp; return None instead of raising."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def window_minutes(change):
    """Scheduled window length in minutes, or None if unusable."""
    start = parse_time(change.get("scheduled_start"))
    end = parse_time(change.get("scheduled_end"))
    if start is None or end is None:
        return None
    return int((end - start).total_seconds() // 60)


def check_change(change):
    """Run the readiness checks on one change.

    Returns (blockers, warnings, passed) — lists of plain-English lines.
    A blocker must be fixed before CAB can approve; a warning can be
    accepted as a condition.
    """
    blockers, warnings, passed = [], [], []
    risk = str(change.get("risk", "")).lower()
    change_type = str(change.get("change_type", "normal")).lower()
    test = change.get("test_evidence") or {}
    rollback = change.get("rollback") or {}
    impact = change.get("impact") or {}
    comms = change.get("communications") or {}
    approvals = change.get("approvals") or []

    # 1. Description — CAB cannot approve what it cannot understand.
    description = (change.get("description") or "").strip()
    if len(description) < MIN_DESCRIPTION_CHARS:
        blockers.append("Description is missing or too short for CAB to assess the change")
    else:
        passed.append("Description explains what is changing and why")

    # 2. Risk — assessed, and a value the process recognises.
    if risk not in VALID_RISKS:
        blockers.append(f"Risk is not assessed (got {change.get('risk')!r}, expected low/medium/high)")
    else:
        passed.append(f"Risk assessed: {risk}")

    # 3. Impact — the affected services must be named.
    if not impact.get("services"):
        blockers.append("Impact does not name the affected services")
    else:
        passed.append("Impact names affected services: " + ", ".join(impact["services"]))

    # 4. Test evidence — tested somewhere that is not production, and passed.
    result = str(test.get("result", "")).lower()
    if result != "pass":
        blockers.append(f"No passing test evidence (result: {test.get('result') or 'not recorded'})")
    elif str(test.get("environment", "")).lower() in ("", "production", "prod"):
        blockers.append("Test evidence does not show a non-production environment")
    else:
        passed.append(f"Tested in {test['environment']}: pass")

    # 5. The CHG-8841 rule — high-risk changes and anything that moves a
    #    limit (pool size, timeout, quota) need load-test evidence.
    if risk == "high" or change.get("touches_limits"):
        if test.get("load_tested"):
            passed.append("Load test evidence present (required for high-risk / limit changes)")
        else:
            blockers.append("High-risk or limit-changing change with no load-test evidence (the CHG-8841 rule)")
    elif test.get("load_tested"):
        passed.append("Load test evidence present")

    # 6. Rollback — a plan, a trigger that is a real condition, and a time.
    if not (rollback.get("plan") or "").strip():
        blockers.append("No rollback plan")
    else:
        passed.append("Rollback plan documented")
    trigger = (rollback.get("trigger") or "").strip()
    if trigger.lower() in PLACEHOLDER_TRIGGERS:
        blockers.append("No rollback trigger — nobody has defined when to back out")
    else:
        passed.append("Rollback trigger defined")
    rollback_minutes = rollback.get("estimated_minutes")
    if not isinstance(rollback_minutes, (int, float)) or rollback_minutes <= 0:
        blockers.append("Rollback time is not estimated")
        rollback_minutes = None

    # 7. Window — valid, and long enough to implement AND still roll back.
    win = window_minutes(change)
    duration = change.get("estimated_duration_minutes")
    if win is None or win <= 0:
        blockers.append("Scheduled window is missing or invalid (end must be after start)")
    elif not isinstance(duration, (int, float)) or duration <= 0:
        blockers.append("Implementation duration is not estimated")
    elif rollback_minutes is not None:
        needed = duration + rollback_minutes
        if needed > win:
            blockers.append(
                f"Window too short to roll back: implementation {int(duration)}m + "
                f"rollback {int(rollback_minutes)}m = {int(needed)}m in a {win}m window")
        elif needed > TIGHT_WINDOW_SHARE * win:
            warnings.append(
                f"Window is tight: implementation + rollback uses {int(needed)}m "
                f"of the {win}m window — no room for trouble")
        else:
            passed.append(f"Window fits implementation + rollback ({int(needed)}m of {win}m)")

    # 8. Approvals — approved, by someone other than the implementer,
    #    and CAB-approved when the risk is high.
    approved = [a for a in approvals if str(a.get("status", "")).lower() == "approved"]
    pending = [a for a in approvals if str(a.get("status", "")).lower() != "approved"]
    if not approvals:
        blockers.append("No approvals recorded")
    elif pending:
        names = ", ".join(f"{a.get('approver', '?')} ({a.get('role', 'approver')})" for a in pending)
        blockers.append(f"Approval still outstanding: {names}")
    else:
        passed.append("All recorded approvals are approved")
    implementer = change.get("implementer")
    if implementer and approved and all(a.get("approver") == implementer for a in approved):
        blockers.append("Implementer is the only approver — no separation of duties")
    if risk == "high" and change_type != "standard" and not change.get("cab_approved"):
        blockers.append("High-risk change without CAB approval")
    elif risk == "high" and change.get("cab_approved"):
        passed.append("CAB approval recorded (required for high risk)")

    # 9. Communications — an expected outage with no notice is a blocker;
    #    a missing notice on a quiet change is a condition.
    if comms.get("stakeholders_notified"):
        passed.append("Stakeholders notified")
    elif impact.get("outage_expected"):
        blockers.append("Outage expected but stakeholders have not been notified")
    else:
        warnings.append("Stakeholders not yet notified (no outage expected)")

    # 10. Dependencies — unchecked dependencies block a high-risk change,
    #     and are a condition on anything else.
    if change.get("dependencies_checked"):
        passed.append("Dependencies checked")
    elif risk == "high":
        blockers.append("Dependencies not checked on a high-risk change")
    else:
        warnings.append("Dependencies not checked")

    # 11. Peer review — expected on medium/high risk.
    if change.get("peer_reviewed"):
        passed.append("Peer reviewed")
    elif risk in ("medium", "high"):
        warnings.append("No peer review recorded for a medium/high-risk change")

    # 12. Verification — how will anyone know it worked?
    if change.get("verification_steps"):
        passed.append(f"Post-implementation verification defined ({len(change['verification_steps'])} steps)")
    else:
        blockers.append("No post-implementation verification steps")

    return blockers, warnings, passed


def verdict(blockers, warnings):
    if blockers:
        return "NOT READY"
    if warnings:
        return "READY WITH CONDITIONS"
    return "READY"


VERDICT_ICON = {"READY": "🟢", "READY WITH CONDITIONS": "🟡", "NOT READY": "🔴"}


def assess(changes):
    """Assess every change; returns a list of result dicts."""
    results = []
    for change in changes:
        blockers, warnings, passed = check_change(change)
        results.append({
            "change": change,
            "blockers": blockers,
            "warnings": warnings,
            "passed": passed,
            "verdict": verdict(blockers, warnings),
        })
    return results


def overall_verdict(results):
    verdicts = [r["verdict"] for r in results]
    if "NOT READY" in verdicts:
        return "NOT READY"
    if "READY WITH CONDITIONS" in verdicts:
        return "READY WITH CONDITIONS"
    return "READY"


def fmt_window(change):
    start = (change.get("scheduled_start") or "—").replace("T", " ")
    end = (change.get("scheduled_end") or "—").replace("T", " ")
    win = window_minutes(change)
    suffix = f" ({win}m)" if win else ""
    return f"{start} → {end}{suffix}"


def render(data, results, generated_at):
    overall = overall_verdict(results)
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("READY", "READY WITH CONDITIONS", "NOT READY")}
    total_blockers = sum(len(r["blockers"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    lines = []
    lines.append("# Change Request Readiness Report")
    lines.append("")
    lines.append(f"**Review:** {data.get('review_for', 'Change review')} | "
                 f"**Generated:** {generated_at} ({data.get('timezone', 'local time')})")
    lines.append("")
    if overall == "NOT READY":
        lines.append(f"## 🔴 NOT READY — {counts['NOT READY']} of {len(results)} changes blocked "
                     f"({total_blockers} blockers, {total_warnings} warnings)")
        lines.append("")
        lines.append("Do not approve the blocked changes at CAB until their blockers are cleared. "
                     "The ready changes can proceed on their own windows.")
    elif overall == "READY WITH CONDITIONS":
        lines.append(f"## 🟡 READY WITH CONDITIONS — {total_warnings} warning(s) to accept or clear")
        lines.append("")
        lines.append("No blockers. CAB can approve, with the warnings below recorded as conditions.")
    else:
        lines.append("## 🟢 READY — every change passes the readiness checks")
    lines.append("")
    lines.append(f"**Summary:** {counts['READY']} ready · "
                 f"{counts['READY WITH CONDITIONS']} ready with conditions · "
                 f"{counts['NOT READY']} not ready · {len(results)} changes checked")
    lines.append("")
    lines.append("| Change | Service | Risk | Window | Verdict | Blockers | Warnings |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        c = r["change"]
        lines.append(f"| {c.get('change_id', '—')} — {c.get('title', '—')} | {c.get('service', '—')} "
                     f"| {c.get('risk', '—')} | {fmt_window(c)} "
                     f"| {VERDICT_ICON[r['verdict']]} {r['verdict']} "
                     f"| {len(r['blockers'])} | {len(r['warnings'])} |")
    lines.append("")

    lines.append("## Actions for CAB (blockers first)")
    lines.append("")
    actions = []
    for r in results:
        for b in r["blockers"]:
            actions.append(f"- 🔴 **{r['change'].get('change_id', '—')}** — {b}")
    for r in results:
        for w in r["warnings"]:
            actions.append(f"- 🟡 **{r['change'].get('change_id', '—')}** — {w}")
    lines.extend(actions or ["- None — every change is ready."])
    lines.append("")

    lines.append("## Change detail")
    for r in results:
        c = r["change"]
        lines.append("")
        lines.append(f"### {VERDICT_ICON[r['verdict']]} {c.get('change_id', '—')} — "
                     f"{c.get('title', 'Untitled')} — {r['verdict']}")
        lines.append("")
        lines.append(f"- **Service:** {c.get('service', '—')} · **Risk:** {c.get('risk', '—')} · "
                     f"**Type:** {c.get('change_type', 'normal')} · "
                     f"**Implementer:** {c.get('implementer', '—')}")
        lines.append(f"- **Window:** {fmt_window(c)} · "
                     f"**Estimated implementation:** {c.get('estimated_duration_minutes', '—')}m")
        if r["blockers"]:
            lines.append("- **Blockers:**")
            lines.extend(f"  - 🔴 {b}" for b in r["blockers"])
        if r["warnings"]:
            lines.append("- **Warnings:**")
            lines.extend(f"  - 🟡 {w}" for w in r["warnings"])
        if r["passed"]:
            lines.append("- **Checks passed:**")
            lines.extend(f"  - ✅ {p}" for p in r["passed"])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Practice scenario with sample data, built for this portfolio — not employer work. "
                 "This report supports the CAB decision; it does not approve or implement any change.*")
    lines.append("")
    return "\n".join(lines), overall


def load_changes(path):
    """Load and shape-check the input. Returns (data, changes) or raises ValueError."""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if isinstance(data, list):
        data = {"changes": data}
    if not isinstance(data, dict) or not isinstance(data.get("changes"), list) or not data["changes"]:
        raise ValueError("input must be a JSON object with a non-empty 'changes' list")
    for i, change in enumerate(data["changes"], start=1):
        if not isinstance(change, dict) or not change.get("change_id"):
            raise ValueError(f"change #{i} must be an object with a change_id")
    return data, data["changes"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check change requests for CAB readiness.")
    parser.add_argument("input", type=Path, help="Change requests JSON (see sample_data/change_requests.json)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output report (default: output/change_readiness_report.md)")
    parser.add_argument("--change", default=None,
                        help="Check only this change_id (e.g. CHG-8901)")
    parser.add_argument("--generated-at", default=None,
                        help="Timestamp to stamp on the report (default: now)")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2
    try:
        data, changes = load_changes(args.input)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.change:
        changes = [c for c in changes if c.get("change_id") == args.change]
        if not changes:
            print(f"ERROR: change {args.change} not found in {args.input}", file=sys.stderr)
            return 2

    results = assess(changes)
    generated_at = args.generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    text, overall = render(data, results, generated_at)

    out = args.out or Path("output") / "change_readiness_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)

    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("READY", "READY WITH CONDITIONS", "NOT READY")}
    print(f"{overall}: {counts['READY']} ready, "
          f"{counts['READY WITH CONDITIONS']} with conditions, "
          f"{counts['NOT READY']} not ready — wrote {out}")
    return 0 if overall == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
