#!/usr/bin/env python3
"""
Day 13 — Service Health / Uptime Checker

Scenario: Thursday, 09:20. The morning BAU health check. Six internal
services are probed every 5 minutes and the results land in a probe
log. Support needs one answer before the business day starts: which
services are actually up, which are slow, which are down — and is the
CRM sync outage that users started reporting at 09:00 real, and how
long has it been going on?

What it checks, per service:
  1. Uptime over the window — successful probes / total probes,
     compared against the service's SLA.
  2. Current state — UP, DEGRADED (up but slow or under SLA), DOWN
     (failing right now, consecutive failures), or UNKNOWN (no
     probes in the window at all).
  3. Latency — average and p95 against the service's max-latency
     threshold. A service answering in 1,250 ms against an 800 ms
     threshold is up, but it is not healthy.
  4. Outage detail — when the current failure run started, how long
     it has lasted, how many consecutive probes failed, and the last
     error seen, so the escalation names facts, not guesses.

Verdict: ALL HEALTHY, DEGRADED, or CRITICAL (a critical service is
DOWN). The tool only reads the probe log and reports — it never
restarts a service or clears an alert. Restarting is the platform
team's call; support supplies the evidence.

Exit codes: 0 = ALL HEALTHY, 1 = DEGRADED or CRITICAL, 2 = error
(missing file, bad row, unknown service in the probe log).

Usage:
    python3 health_check.py sample_data/services.json sample_data/probes.csv \
        --out output/health_report.md
"""

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

TS_FORMAT = "%Y-%m-%d %H:%M"


class HealthCheckError(Exception):
    """Bad input file — missing, unreadable, or a bad row."""


def load_services(path):
    """Load the service inventory (name, URL, thresholds, SLA)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise HealthCheckError(f"services file not found: {path}")
    except json.JSONDecodeError as exc:
        raise HealthCheckError(f"services file is not valid JSON: {exc}")
    services = data.get("services", [])
    if not services:
        raise HealthCheckError("services file lists no services")
    for svc in services:
        for key in ("name", "url", "expected_status", "max_latency_ms",
                    "uptime_sla_percent", "critical"):
            if key not in svc:
                raise HealthCheckError(
                    f"service {svc.get('name', '?')} is missing '{key}'")
    return services


def load_probes(path, known_names):
    """Load probe rows, grouped by service, newest last.

    A row is a success when its HTTP status matches the service's
    expected status and the error field is empty. Anything else is a
    failure. Latency is only meaningful on a probe that answered.
    """
    try:
        fh = open(path, newline="", encoding="utf-8")
    except FileNotFoundError:
        raise HealthCheckError(f"probe file not found: {path}")
    probes = {name: [] for name in known_names}
    with fh:
        reader = csv.DictReader(fh)
        required = {"timestamp", "service", "http_status", "latency_ms", "error"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise HealthCheckError(
                f"probe file must have columns: {sorted(required)}")
        for line_no, row in enumerate(reader, start=2):
            name = (row.get("service") or "").strip()
            if name not in probes:
                raise HealthCheckError(
                    f"line {line_no}: probe for unknown service '{name}'")
            try:
                ts = datetime.strptime((row.get("timestamp") or "").strip(),
                                       TS_FORMAT)
            except ValueError:
                raise HealthCheckError(
                    f"line {line_no}: bad timestamp "
                    f"'{row.get('timestamp')}' (expected YYYY-MM-DD HH:MM)")
            try:
                status = int((row.get("http_status") or "").strip())
            except ValueError:
                raise HealthCheckError(
                    f"line {line_no}: bad http_status '{row.get('http_status')}'")
            latency_raw = (row.get("latency_ms") or "").strip()
            latency = None
            if latency_raw:
                try:
                    latency = int(latency_raw)
                except ValueError:
                    raise HealthCheckError(
                        f"line {line_no}: bad latency_ms '{latency_raw}'")
            probes[name].append({
                "timestamp": ts,
                "status": status,
                "latency_ms": latency,
                "error": (row.get("error") or "").strip(),
            })
    for name in probes:
        probes[name].sort(key=lambda p: p["timestamp"])
    return probes


def percentile(values, pct):
    """Nearest-rank percentile of a non-empty list of numbers."""
    ordered = sorted(values)
    rank = math.ceil(pct / 100 * len(ordered))
    return ordered[max(0, min(rank, len(ordered)) - 1)]


def consecutive_failures(probes, expected_status):
    """How many probes at the end of the list failed in a row."""
    count = 0
    for probe in reversed(probes):
        ok = probe["status"] == expected_status and not probe["error"]
        if ok:
            break
        count += 1
    return count


def analyse_service(service, probes):
    """Summarise one service's probes into a status and the facts."""
    expected = service["expected_status"]
    total = len(probes)
    if total == 0:
        return {"name": service["name"], "status": "UNKNOWN", "total": 0,
                "successes": 0, "failures": 0, "uptime_percent": None,
                "avg_latency_ms": None, "p95_latency_ms": None,
                "consecutive_failures": 0, "outage_since": None,
                "outage_minutes": None, "last_error": None,
                "last_probe": None, "reasons": ["no probes in the window"]}

    successes = [p for p in probes
                 if p["status"] == expected and not p["error"]]
    failures = total - len(successes)
    uptime = round(len(successes) / total * 100, 2)
    latencies = [p["latency_ms"] for p in successes
                 if p["latency_ms"] is not None]
    avg_latency = (round(sum(latencies) / len(latencies))
                   if latencies else None)
    p95 = percentile(latencies, 95) if latencies else None

    fails_in_a_row = consecutive_failures(probes, expected)
    outage_since = None
    outage_minutes = None
    last_error = None
    if fails_in_a_row:
        outage_since = probes[-fails_in_a_row]["timestamp"]
        last_error = probes[-1]["error"] or f"HTTP {probes[-1]['status']}"
        outage_minutes = int((probes[-1]["timestamp"] - outage_since)
                             .total_seconds() // 60)

    reasons = []
    if fails_in_a_row >= 2:
        status = "DOWN"
        reasons.append(f"Failing now — {fails_in_a_row} consecutive "
                       f"failed probes since {outage_since:%H:%M}")
    else:
        status = "UP"
    if uptime < service["uptime_sla_percent"]:
        reasons.append(f"Uptime {uptime:.2f}% is below SLA "
                       f"{service['uptime_sla_percent']:.1f}%")
    if avg_latency is not None and avg_latency > service["max_latency_ms"]:
        reasons.append(f"Average latency {avg_latency} ms exceeds "
                       f"{service['max_latency_ms']} ms threshold")
    if p95 is not None and p95 > 2 * service["max_latency_ms"]:
        reasons.append(f"P95 latency {p95} ms is over twice the "
                       f"{service['max_latency_ms']} ms threshold")
    if status != "DOWN" and reasons:
        status = "DEGRADED"

    return {"name": service["name"], "status": status, "total": total,
            "successes": len(successes), "failures": failures,
            "uptime_percent": uptime, "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95, "consecutive_failures": fails_in_a_row,
            "outage_since": outage_since, "outage_minutes": outage_minutes,
            "last_error": last_error, "last_probe": probes[-1]["timestamp"],
            "reasons": reasons}


def overall_verdict(results, services):
    """Roll the per-service statuses up to one verdict."""
    critical = {s["name"] for s in services if s["critical"]}
    by_status = {}
    for result in results:
        by_status.setdefault(result["status"], []).append(result["name"])
    if any(r["status"] == "DOWN" and r["name"] in critical
           for r in results):
        return "CRITICAL", "a critical service is DOWN"
    if by_status.get("DOWN") or by_status.get("DEGRADED") \
            or by_status.get("UNKNOWN"):
        problems = []
        for status in ("DOWN", "DEGRADED", "UNKNOWN"):
            if by_status.get(status):
                problems.append(
                    f"{len(by_status[status])} {status.lower()}: "
                    + ", ".join(by_status[status]))
        return "DEGRADED", "; ".join(problems)
    return "ALL HEALTHY", "every service is up, within SLA and within latency"


def check_all(services, probes_by_service):
    """Analyse every service and return (results, verdict, reason)."""
    results = [analyse_service(svc, probes_by_service[svc["name"]])
               for svc in services]
    verdict, reason = overall_verdict(results, services)
    return results, verdict, reason


def render_report(results, verdict, reason, services, window_hours, as_of):
    """Render the one-page health report as Markdown."""
    by_name = {s["name"]: s for s in services}
    emoji = {"ALL HEALTHY": "🟢", "DEGRADED": "🟡", "CRITICAL": "🔴"}
    status_emoji = {"UP": "🟢", "DEGRADED": "🟡", "DOWN": "🔴",
                    "UNKNOWN": "⚪"}
    lines = [
        "# Service Health / Uptime Report",
        "",
        f"**As of:** {as_of:%Y-%m-%d %H:%M} · "
        f"**Window:** last {window_hours} hours (probes every 5 minutes)",
        "",
        f"## Verdict: {emoji[verdict]} {verdict}",
        "",
        reason.capitalize() + ".",
        "",
        "## Services",
        "",
        "| Service | Status | Uptime | SLA | Avg latency | p95 | Last probe |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        svc = by_name[r["name"]]
        uptime = (f"{r['uptime_percent']:.2f}%" if r["uptime_percent"] is not None
                  else "—")
        avg = (f"{r['avg_latency_ms']} ms" if r["avg_latency_ms"] is not None
               else "—")
        p95 = (f"{r['p95_latency_ms']} ms" if r["p95_latency_ms"] is not None
               else "—")
        last = (f"{r['last_probe']:%H:%M}" if r["last_probe"] else "—")
        lines.append(
            f"| {r['name']}{' (critical)' if svc['critical'] else ''} | "
            f"{status_emoji[r['status']]} {r['status']} | {uptime} | "
            f"{svc['uptime_sla_percent']:.1f}% | {avg} | {p95} | {last} |")
    lines += ["", "## What needs attention", ""]
    problems = [r for r in results if r["status"] != "UP"]
    if not problems:
        lines.append("Nothing — every service is up, within its SLA, and "
                     "within its latency threshold.")
    for r in problems:
        svc = by_name[r["name"]]
        lines.append(f"### {status_emoji[r['status']]} {r['name']} — "
                     f"{r['status']}")
        lines.append("")
        for reason_text in r["reasons"]:
            lines.append(f"- {reason_text}.")
        if r["outage_since"] is not None:
            lines.append(
                f"- Outage started {r['outage_since']:%Y-%m-%d %H:%M} "
                f"({r['outage_minutes']} minutes ago); last error: "
                f"\"{r['last_error']}\".")
        lines.append(
            f"- {r['failures']} failed of {r['total']} probes in the "
            f"window; latency threshold {svc['max_latency_ms']} ms, "
            f"SLA {svc['uptime_sla_percent']:.1f}%.")
        lines.append("")
    lines += [
        "## Actions",
        "",
    ]
    if verdict == "ALL HEALTHY":
        lines.append("- No action. File the report with the morning BAU notes.")
    else:
        for r in problems:
            if r["status"] == "DOWN":
                lines.append(
                    f"- Escalate {r['name']} to the platform team now — "
                    f"down since {r['outage_since']:%H:%M} "
                    f"({r['outage_minutes']} min), "
                    f"{r['consecutive_failures']} consecutive failed "
                    f"probes, last error \"{r['last_error']}\".")
            elif r["status"] == "DEGRADED":
                lines.append(
                    f"- Raise {r['name']} with the service owner — "
                    f"{'; '.join(r['reasons'])}.")
            else:
                lines.append(
                    f"- Check why {r['name']} has no probes in the window "
                    f"— the prober itself may be down.")
        lines.append("- Re-run this check after any fix and keep both "
                     "reports — the before/after is the incident record.")
    lines += [
        "",
        "_Practice scenario with sample data, built for this portfolio — "
        "not employer work._",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Service health / uptime checker — one report from "
                    "the probe log.")
    parser.add_argument("services", help="services.json inventory")
    parser.add_argument("probes", help="probes.csv probe log")
    parser.add_argument("--window-hours", type=int, default=24,
                        help="window the probe log covers (default: 24)")
    parser.add_argument("--out", help="write the Markdown report here")
    args = parser.parse_args(argv)

    try:
        services = load_services(args.services)
        probes = load_probes(args.probes,
                             [s["name"] for s in services])
    except HealthCheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    results, verdict, reason = check_all(services, probes)
    as_of = max((r["last_probe"] for r in results if r["last_probe"]),
                default=None)
    report = render_report(results, verdict, reason, services,
                           args.window_hours, as_of)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"report written to {out_path}")
    else:
        print(report)

    down = sum(1 for r in results if r["status"] == "DOWN")
    degraded = sum(1 for r in results if r["status"] in ("DEGRADED", "UNKNOWN"))
    print(f"Verdict: {verdict} — {len(results)} services checked, "
          f"{down} down, {degraded} degraded/unknown.")
    return 0 if verdict == "ALL HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(main())
