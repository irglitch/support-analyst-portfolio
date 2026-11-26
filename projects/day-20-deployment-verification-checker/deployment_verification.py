#!/usr/bin/env python3
"""Deployment Verification Checker — Day 20 of the support analyst portfolio.

Scenario: Thursday 09:20, the change manager wants last night's six
change tickets closed before the 10:00 settlement batch. A deployment
tool saying "success" is not proof the change is live: one instance can
still run the old build, a renewed certificate can sit in the vault
while the endpoint serves the old one, and a change CAB deferred can
quietly be present anyway. Closing the tickets without checking is how
"deployed" becomes next week's incident.

This tool compares what each change was supposed to do (the expected
outcome from the CAB decision) against what is actually observed this
morning — deployment status, the version and config on every instance,
health, the smoke test, the post-deployment error rate against its
warning level and rollback trigger, the live certificate expiry, and
whether the work finished inside its window. Each deployment gets a
verdict — VERIFIED, VERIFIED WITH WARNINGS, or FAILED — and the report
ends with a ranked action list (rollbacks first). Changes CAB held are
verified too: "correctly not deployed" is a result worth proving.

Exit codes: 0 = every deployment VERIFIED, 1 = warnings or failures
found (action needed before the tickets close), 2 = error (file
missing / unreadable / wrong shape).

Usage:
  python3 deployment_verification.py sample_data/deployments.json
  python3 deployment_verification.py sample_data/deployments.json \\
      --out output/deployment_verification_report.md --generated-at "2026-11-26 09:20"
  python3 deployment_verification.py sample_data/deployments.json --deployment CHG-8853

Python standard library only. The tool only reads and reports — it
never deploys, restarts, or rolls back anything; those calls belong to
the change owner and the duty manager.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

VALID_OUTCOMES = ("deployed", "held")
VALID_STATUSES = ("completed", "failed", "in_progress", "not_deployed")


def parse_time(value):
    """Parse an ISO timestamp; return None instead of raising."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """Parse an ISO date; return None instead of raising."""
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def check_deployment(deployment):
    """Run the verification checks on one deployment.

    Returns (failures, warnings, passed) — lists of plain-English lines.
    A failure means the deployment is not verified and the change ticket
    must stay open; a warning can be recorded on the ticket and closed.
    """
    failures, warnings, passed = [], [], []
    expected = deployment.get("expected") or {}
    observed = deployment.get("observed") or {}
    outcome = str(expected.get("outcome", "")).lower()
    status = str(observed.get("deployment_status", "")).lower()
    instances = observed.get("instances") or []

    # 1. Outcome — did what CAB decided actually happen?
    if outcome not in VALID_OUTCOMES:
        failures.append(f"Expected outcome is not recorded (got {expected.get('outcome')!r}, "
                        "expected deployed/held) — cannot verify against the CAB decision")
        return failures, warnings, passed
    if status not in VALID_STATUSES:
        failures.append(f"Deployment status is not recorded (got {observed.get('deployment_status')!r}) "
                        "— cannot verify")
        return failures, warnings, passed

    if outcome == "held":
        if status != "not_deployed":
            failures.append(f"Deployed despite the CAB deferral (status: {status}) — "
                            "escalate to the change manager before anything else")
        else:
            passed.append("Correctly not deployed — the CAB deferral held")
        previous = expected.get("previous_version")
        if previous:
            wrong = [i.get("name", "?") for i in instances
                     if i.get("version") != previous]
            if wrong:
                failures.append(f"Version changed on {', '.join(wrong)} although the change "
                                f"was held (expected {previous} everywhere)")
            elif instances:
                passed.append(f"Version unchanged at {previous} on all {len(instances)} instance(s)")
        health = str(observed.get("health", "")).lower()
        if health == "ok":
            passed.append("Health endpoint OK")
        elif health:
            failures.append(f"Health endpoint reports {observed.get('health')!r} on a held change — "
                            "investigate before closing")
        return failures, warnings, passed

    # outcome == "deployed"
    if status == "failed":
        failures.append("Deployment reported FAILED — the change is not live")
        return failures, warnings, passed
    if status == "in_progress":
        failures.append("Deployment still in progress this morning — not verified; "
                        "the window has overrun")
        return failures, warnings, passed
    if status == "not_deployed":
        failures.append("Expected to deploy but no deployment happened — the change is not live")
        return failures, warnings, passed
    passed.append("Deployment completed")

    # 2. Every expected instance must be reporting — an instance nobody
    #    can see is an instance nobody verified.
    expected_count = expected.get("instances")
    if isinstance(expected_count, int) and expected_count > 0:
        if len(instances) != expected_count:
            failures.append(f"Only {len(instances)} of {expected_count} expected instances "
                            "reporting — the missing instance(s) cannot be verified")
        else:
            passed.append(f"All {expected_count} expected instances reporting")

    # 3. Version — the new build must be on every instance. One instance
    #    on the old build is a partial deployment, not a deployment.
    want_version = expected.get("version")
    if want_version:
        stale = [f"{i.get('name', '?')} ({i.get('version', 'unknown')})"
                 for i in instances if i.get("version") != want_version]
        if stale:
            failures.append(f"Partial deployment — expected {want_version} everywhere, "
                            f"still on the old build: {', '.join(stale)}")
        elif instances:
            passed.append(f"Version {want_version} live on all {len(instances)} instance(s)")

    # 4. Config — the values the change was made for must read back.
    want_config = expected.get("config") or {}
    for key, want in want_config.items():
        wrong = [f"{i.get('name', '?')} ({(i.get('config') or {}).get(key, 'not set')})"
                 for i in instances if (i.get("config") or {}).get(key) != want]
        if wrong:
            failures.append(f"Config {key} should be {want} but reads: {', '.join(wrong)}")
        elif instances:
            passed.append(f"Config {key} = {want} on every instance")

    # 5. Health — the service must answer healthy after the change.
    health = str(observed.get("health", "")).lower()
    if health == "ok":
        passed.append("Health endpoint OK")
    elif health == "degraded":
        warnings.append("Health endpoint reports degraded after the deployment")
    elif health:
        failures.append(f"Health endpoint reports {observed.get('health')!r} after the deployment")
    else:
        warnings.append("No health result recorded — verify the service manually")

    # 6. Smoke test — the end-to-end check the change promised.
    if expected.get("smoke_test"):
        result = str(observed.get("smoke_test_result", "")).lower()
        if result == "pass":
            passed.append(f"Smoke test passed ({expected['smoke_test']})")
        elif result == "fail":
            detail = observed.get("smoke_test_detail") or "no detail recorded"
            failures.append(f"Smoke test FAILED ({expected['smoke_test']}): {detail}")
        else:
            failures.append(f"Smoke test not run ({expected['smoke_test']}) — "
                            "a deployment nobody exercised is not verified")

    # 7. Error rate — above the warning level is a condition; above the
    #    rollback trigger the change's own plan says back out.
    rate = observed.get("error_rate_pct")
    warn_at = expected.get("max_error_rate_pct")
    trigger = expected.get("rollback_trigger_pct")
    if isinstance(rate, (int, float)):
        if isinstance(trigger, (int, float)) and rate > trigger:
            failures.append(f"Error rate {rate}% breached the rollback trigger ({trigger}%) — "
                            "roll back per the change plan")
        elif isinstance(warn_at, (int, float)) and rate > warn_at:
            warnings.append(f"Error rate {rate}% is above the {warn_at}% warning level "
                            f"(rollback trigger {trigger}%) — watch closely")
        else:
            passed.append(f"Error rate {rate}% within limits")
    else:
        warnings.append("No post-deployment error rate recorded — confirm monitoring is watching")

    # 8. Certificate — the live endpoint must serve the new certificate,
    #    not just have it sitting in the vault.
    cert_min = parse_date(expected.get("cert_expiry_on_or_after"))
    if cert_min:
        live = parse_date(observed.get("cert_expiry_live"))
        if live is None:
            failures.append("Live certificate expiry not recorded — cannot verify the renewal is serving")
        elif live < cert_min:
            failures.append(f"Live endpoint still serves the old certificate (expires {live}, "
                            f"expected on/after {cert_min}) — the renewal is not live")
        else:
            passed.append(f"Live certificate expires {live} — renewal is serving")

    # 9. Window — finishing late is a record for CAB, not a failure of
    #    the change itself, unless the overrun is still running (check 1).
    window_end = parse_time(expected.get("window_end"))
    completed = parse_time(observed.get("completed_at"))
    if window_end and completed:
        if completed > window_end:
            overrun = int((completed - window_end).total_seconds() // 60)
            warnings.append(f"Completed {overrun}m after the window closed "
                            f"({expected.get('window_end')}) — record the overrun on the ticket")
        else:
            passed.append("Completed inside the scheduled window")

    return failures, warnings, passed


def verdict(failures, warnings):
    if failures:
        return "FAILED"
    if warnings:
        return "VERIFIED WITH WARNINGS"
    return "VERIFIED"


VERDICT_ICON = {"VERIFIED": "🟢", "VERIFIED WITH WARNINGS": "🟡", "FAILED": "🔴"}


def assess(deployments):
    """Assess every deployment; returns a list of result dicts."""
    results = []
    for deployment in deployments:
        failures, warnings, passed = check_deployment(deployment)
        results.append({
            "deployment": deployment,
            "failures": failures,
            "warnings": warnings,
            "passed": passed,
            "verdict": verdict(failures, warnings),
        })
    return results


def overall_verdict(results):
    verdicts = [r["verdict"] for r in results]
    if "FAILED" in verdicts:
        return "FAILED"
    if "VERIFIED WITH WARNINGS" in verdicts:
        return "VERIFIED WITH WARNINGS"
    return "VERIFIED"


def render(data, results, generated_at):
    overall = overall_verdict(results)
    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("VERIFIED", "VERIFIED WITH WARNINGS", "FAILED")}
    total_failures = sum(len(r["failures"]) for r in results)
    total_warnings = sum(len(r["warnings"]) for r in results)

    lines = []
    lines.append("# Deployment Verification Report")
    lines.append("")
    lines.append(f"**Window:** {data.get('window', 'Deployment window')} | "
                 f"**Generated:** {generated_at} ({data.get('timezone', 'local time')})")
    lines.append("")
    if overall == "FAILED":
        lines.append(f"## 🔴 FAILED — {counts['FAILED']} of {len(results)} deployments not verified "
                     f"({total_failures} failure{'s' if total_failures != 1 else ''}, "
                     f"{total_warnings} warning{'s' if total_warnings != 1 else ''})")
        lines.append("")
        lines.append("Do not close the failed change tickets. The verified changes can close; "
                     "the failures below need a fix or a rollback first.")
    elif overall == "VERIFIED WITH WARNINGS":
        lines.append(f"## 🟡 VERIFIED WITH WARNINGS — {total_warnings} warning(s) to record on the tickets")
        lines.append("")
        lines.append("Every deployment is live as intended. Record the warnings below on their "
                     "change tickets before closing them.")
    else:
        lines.append("## 🟢 VERIFIED — every deployment matches its CAB decision")
    lines.append("")
    lines.append(f"**Summary:** {counts['VERIFIED']} verified · "
                 f"{counts['VERIFIED WITH WARNINGS']} verified with warnings · "
                 f"{counts['FAILED']} failed · {len(results)} deployments checked")
    lines.append("")
    lines.append("| Change | Service | Expected | Observed | Verdict | Failures | Warnings |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        d = r["deployment"]
        expected = d.get("expected") or {}
        observed = d.get("observed") or {}
        want = expected.get("version") or expected.get("outcome", "—")
        lines.append(f"| {d.get('deployment_id', '—')} — {d.get('title', '—')} | {d.get('service', '—')} "
                     f"| {want} | {observed.get('deployment_status', '—')} "
                     f"| {VERDICT_ICON[r['verdict']]} {r['verdict']} "
                     f"| {len(r['failures'])} | {len(r['warnings'])} |")
    lines.append("")

    lines.append("## Actions (failures first)")
    lines.append("")
    actions = []
    for r in results:
        for f in r["failures"]:
            actions.append(f"- 🔴 **{r['deployment'].get('deployment_id', '—')}** — {f}")
    for r in results:
        for w in r["warnings"]:
            actions.append(f"- 🟡 **{r['deployment'].get('deployment_id', '—')}** — {w}")
    lines.extend(actions or ["- None — every deployment is verified."])
    lines.append("")

    lines.append("## Deployment detail")
    for r in results:
        d = r["deployment"]
        expected = d.get("expected") or {}
        observed = d.get("observed") or {}
        lines.append("")
        lines.append(f"### {VERDICT_ICON[r['verdict']]} {d.get('deployment_id', '—')} — "
                     f"{d.get('title', 'Untitled')} — {r['verdict']}")
        lines.append("")
        lines.append(f"- **Service:** {d.get('service', '—')} · "
                     f"**Expected outcome:** {expected.get('outcome', '—')} · "
                     f"**Observed status:** {observed.get('deployment_status', '—')}")
        if observed.get("completed_at"):
            lines.append(f"- **Completed:** {observed['completed_at'].replace('T', ' ')} · "
                         f"**Window ended:** {(expected.get('window_end') or '—').replace('T', ' ')}")
        if r["failures"]:
            lines.append("- **Failures:**")
            lines.extend(f"  - 🔴 {f}" for f in r["failures"])
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
                 "This report verifies deployments; it does not deploy, restart, or roll back anything.*")
    lines.append("")
    return "\n".join(lines), overall


def load_deployments(path):
    """Load and shape-check the input. Returns (data, deployments) or raises ValueError."""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if isinstance(data, list):
        data = {"deployments": data}
    if not isinstance(data, dict) or not isinstance(data.get("deployments"), list) or not data["deployments"]:
        raise ValueError("input must be a JSON object with a non-empty 'deployments' list")
    for i, deployment in enumerate(data["deployments"], start=1):
        if not isinstance(deployment, dict) or not deployment.get("deployment_id"):
            raise ValueError(f"deployment #{i} must be an object with a deployment_id")
    return data, data["deployments"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify last night's deployments against their CAB decisions.")
    parser.add_argument("input", type=Path, help="Deployments JSON (see sample_data/deployments.json)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output report (default: output/deployment_verification_report.md)")
    parser.add_argument("--deployment", default=None,
                        help="Check only this deployment_id (e.g. CHG-8853)")
    parser.add_argument("--generated-at", default=None,
                        help="Timestamp to stamp on the report (default: now)")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 2
    try:
        data, deployments = load_deployments(args.input)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.deployment:
        deployments = [d for d in deployments if d.get("deployment_id") == args.deployment]
        if not deployments:
            print(f"ERROR: deployment {args.deployment} not found in {args.input}", file=sys.stderr)
            return 2

    results = assess(deployments)
    generated_at = args.generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    text, overall = render(data, results, generated_at)

    out = args.out or Path("output") / "deployment_verification_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)

    counts = {v: sum(1 for r in results if r["verdict"] == v)
              for v in ("VERIFIED", "VERIFIED WITH WARNINGS", "FAILED")}
    print(f"{overall}: {counts['VERIFIED']} verified, "
          f"{counts['VERIFIED WITH WARNINGS']} with warnings, "
          f"{counts['FAILED']} failed — wrote {out}")
    return 0 if overall == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
