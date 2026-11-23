#!/usr/bin/env python3
"""Daily BAU Health-Check Report — Day 17 of the support analyst portfolio.

Scenario: every morning at 09:20 the support team runs one health check
before the business day starts. Until now the checks lived in five
different places — a service probe log, a disk report, the incident
queue, the file-transfer manifest and the certificate inventory — so the
morning check meant opening five tools and stitching the picture
together by hand. This tool reads one snapshot of each (CSV, produced
by the checks in Days 02/04/05/13/14/15, or by the live collector in
run_bau_check.sh) and writes a single one-page BAU report: an overall
verdict (GREEN / AMBER / RED), a status per area, and a ranked action
list so the team works the worst item first.

Usage:
    python3 bau_report.py --input-dir sample_data --as-of 2026-11-23T09:20
    python3 bau_report.py --input-dir sample_data --as-of 2026-11-23T09:20 \\
        --out output/bau_report.md

    # Live snapshot first, then the report (see run_bau_check.sh):
    ./run_bau_check.sh --live

Exit codes (so a scheduler can alert on them):
    0  GREEN — every area OK
    1  AMBER — at least one WARNING, nothing worse
    2  RED   — at least one CRITICAL item, or a required input is missing

Python standard library only. The tool only reads and reports — it
never restarts a service, deletes a file or renews a certificate.
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

INPUT_FILES = ("services.csv", "disks.csv", "sla.csv", "files.csv", "certs.csv")

# SLA resolution targets by priority (hours) — same targets as Day 05.
SLA_TARGETS_HOURS = {"P1": 4, "P2": 8, "P3": 24, "P4": 48}
AT_RISK_HOURS = 2          # breach within 2 hours: AT RISK
AT_RISK_FRACTION = 0.25    # ...or under 25% of the SLA target left: AT RISK

DISK_WARN_PCT = 80
DISK_FAIL_PCT = 90

CERT_WARN_DAYS = 30
CERT_CRIT_DAYS = 14

# Worst first — used to rank sections, items and the overall verdict.
SEVERITY_ORDER = ["CRITICAL", "WARNING", "OK"]
STATUS_ICON = {"CRITICAL": "🔴", "WARNING": "🟡", "OK": "🟢"}
VERDICT = {"CRITICAL": ("🔴 RED", 2), "WARNING": ("🟡 AMBER", 1), "OK": ("🟢 GREEN", 0)}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build the daily BAU health-check report from CSV snapshots.")
    parser.add_argument("--input-dir", default="sample_data",
                        help="Directory holding services.csv, disks.csv, sla.csv, "
                             "files.csv and certs.csv (default: sample_data)")
    parser.add_argument("--as-of", default=None,
                        help="Reference datetime, ISO format e.g. 2026-11-23T09:20 "
                             "(default: now). Use it to reproduce a report.")
    parser.add_argument("--out", default=None, help="Write the report to this file")
    return parser.parse_args(argv)


def parse_dt(value):
    """Accept 'YYYY-MM-DD HH:MM' or a full ISO datetime."""
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(value)


def parse_date(value):
    value = value.strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return datetime.fromisoformat(value).date()


def read_csv(path):
    with open(path, newline="") as f:
        return [{k: (v.strip() if isinstance(v, str) else v)
                 for k, v in row.items()} for row in csv.DictReader(f)]


def _float(value, default=None):
    try:
        return float(value) if value not in ("", None) else default
    except (TypeError, ValueError):
        return default


def _int(value, default=None):
    result = _float(value, default)
    return int(result) if result is not None else default


def load_inputs(input_dir):
    """Read all five snapshot files. Raises FileNotFoundError naming the file."""
    data = {}
    for name in INPUT_FILES:
        path = Path(input_dir) / name
        if not path.is_file():
            raise FileNotFoundError(f"missing input file: {path}")
        data[name] = read_csv(path)
    return data


# --- Section checks -------------------------------------------------------

def check_services(rows):
    """One row per service. DOWN is CRITICAL; a latency or uptime breach
    on an UP service is WARNING (degraded, not down)."""
    items = []
    for row in rows:
        latency = _int(row.get("latency_ms"))
        threshold = _int(row.get("latency_threshold_ms"))
        uptime = _float(row.get("uptime_pct"))
        sla = _float(row.get("uptime_sla_pct"))
        failed = _int(row.get("failed_probes"), 0)
        reported = (row.get("status") or "").strip().upper()
        if reported == "DOWN":
            status = "CRITICAL"
        elif reported == "DEGRADED":
            status = "WARNING"
        elif latency is not None and threshold is not None and latency > threshold:
            status = "WARNING"
        elif uptime is not None and sla is not None and uptime < sla:
            status = "WARNING"
        else:
            status = "OK"
        items.append({
            "service": row.get("service", "?"),
            "status": reported or "UNKNOWN",
            "severity": status,
            "latency": latency,
            "threshold": threshold,
            "uptime": uptime,
            "sla": sla,
            "failed": failed,
            "last_error": row.get("last_error", ""),
            "down_since": row.get("down_since", ""),
        })
    return items


def check_disks(rows):
    """FAIL at 90% used (or inodes), WARN at 80%. Hours-to-full comes
    from the growth rate; a disk not growing has no deadline."""
    items = []
    for row in rows:
        used = _float(row.get("used_pct"), 0)
        inodes = _float(row.get("inodes_pct"), 0)
        growth = _float(row.get("growth_pct_per_hour"), 0)
        if used >= DISK_FAIL_PCT or inodes >= DISK_FAIL_PCT:
            severity = "CRITICAL"
        elif used >= DISK_WARN_PCT or inodes >= DISK_WARN_PCT:
            severity = "WARNING"
        else:
            severity = "OK"
        hours = (100 - used) / growth if growth and growth > 0 else None
        items.append({
            "mount": row.get("mount", "?"),
            "total_gb": _float(row.get("total_gb")),
            "used": used,
            "inodes": inodes,
            "growth": growth,
            "hours_to_full": hours,
            "severity": severity,
        })
    return items


def check_sla(rows, as_of):
    """Open tickets only — resolved tickets are excluded. Deadline is
    opened + priority target. BREACHED is CRITICAL, AT RISK is WARNING
    (under 2 hours left, or under 25% of the target left). An unknown
    priority is flagged for a manual check instead of crashing the run."""
    items = []
    for row in rows:
        if (row.get("status") or "").strip().lower() != "open":
            continue
        priority = (row.get("priority") or "").strip().upper()
        opened = parse_dt(row["opened"])
        target = SLA_TARGETS_HOURS.get(priority)
        if target is None:
            items.append({
                "ticket": row.get("ticket", "?"),
                "priority": priority,
                "summary": row.get("summary", ""),
                "severity": "WARNING",
                "detail": "unknown priority — check the SLA target by hand",
                "owner": row.get("owner", ""),
            })
            continue
        deadline = opened + timedelta(hours=target)
        remaining = deadline - as_of
        if remaining.total_seconds() < 0:
            over = -remaining
            severity, detail = "CRITICAL", f"BREACHED {fmt_duration(over)} over SLA"
        elif (remaining <= timedelta(hours=AT_RISK_HOURS)
              or remaining <= timedelta(hours=target * AT_RISK_FRACTION)):
            severity, detail = "WARNING", f"AT RISK — breaches in {fmt_duration(remaining)}"
        else:
            severity, detail = "OK", f"ON TRACK — {fmt_duration(remaining)} left"
        items.append({
            "ticket": row.get("ticket", "?"),
            "priority": priority,
            "summary": row.get("summary", ""),
            "severity": severity,
            "detail": detail,
            "owner": row.get("owner", ""),
            "deadline": deadline,
        })
    return items


def check_files(rows):
    """MISSING is CRITICAL (the downstream batch cannot start). LATE,
    EMPTY or SMALL is WARNING. OK needs an arrival time and a sane size."""
    items = []
    for row in rows:
        status = (row.get("status") or "").strip().upper()
        size = _int(row.get("size_bytes"), 0)
        minimum = _int(row.get("expected_min_bytes"), 0)
        if status == "MISSING":
            severity, detail = "CRITICAL", "never arrived"
        elif status in ("LATE", "EMPTY", "SMALL"):
            severity, detail = "WARNING", status.title()
        elif status == "OK" and size < minimum:
            severity, detail = "WARNING", f"arrived but only {size} bytes"
        elif status == "OK":
            severity, detail = "OK", "arrived on time"
        else:
            severity, detail = "WARNING", f"unknown status '{status}' — check by hand"
        items.append({
            "filename": row.get("filename", "?"),
            "status": status,
            "severity": severity,
            "detail": detail,
            "expected_by": row.get("expected_by", ""),
            "arrived_at": row.get("arrived_at", ""),
            "sender": row.get("sender", ""),
        })
    return items


def check_certs(rows, as_of):
    """Same thresholds as Day 15: EXPIRED / CRITICAL (≤14 days) /
    WARNING (≤30 days) / OK."""
    items = []
    for row in rows:
        expiry = parse_date(row["expiry_date"])
        days = (expiry - as_of.date()).days
        if days < 0:
            severity, detail = "CRITICAL", f"EXPIRED {abs(days)} day(s) ago"
        elif days <= CERT_CRIT_DAYS:
            severity, detail = "CRITICAL", f"expires in {days} day(s)"
        elif days <= CERT_WARN_DAYS:
            severity, detail = "WARNING", f"expires in {days} day(s)"
        else:
            severity, detail = "OK", f"expires in {days} day(s)"
        items.append({
            "hostname": row.get("hostname", "?"),
            "service": row.get("service", ""),
            "expiry": expiry,
            "days": days,
            "severity": severity,
            "detail": detail,
            "owner": row.get("owner", ""),
        })
    return items


def fmt_duration(delta):
    """'1h 35m', '30m', '4h 55m' — never a negative value."""
    total = max(0, int(delta.total_seconds()))
    hours, minutes = divmod(total, 3600)
    minutes //= 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def worst_severity(items):
    """The worst severity in a section (OK when the section is empty)."""
    for severity in SEVERITY_ORDER:
        if any(item["severity"] == severity for item in items):
            return severity
    return "OK"


# --- Ranked actions --------------------------------------------------------

def build_actions(sections, as_of):
    """One action per problem, worst first, then by deadline.

    Order inside CRITICAL: a down service, a missing file, a certificate
    expiring today, a breached ticket, a full disk. Warnings follow the
    same shape, earliest deadline first.
    """
    actions = []

    for item in sections["services"]:
        if item["severity"] == "CRITICAL":
            since = f" since {item['down_since']}" if item["down_since"] else ""
            err = f" — {item['last_error']}" if item["last_error"] else ""
            actions.append((0, 0, f"Page the platform team: **{item['service']}** "
                                  f"is DOWN{since} ({item['failed']} failed probe(s)"
                                  f"{err}). Check the service, then its dependency."))
        elif item["severity"] == "WARNING":
            actions.append((1, 0, f"Investigate **{item['service']}**: DEGRADED — "
                                  f"{item['latency']} ms vs {item['threshold']} ms "
                                  f"threshold. Slow, not down — check the dependency "
                                  f"before it becomes an outage."))

    for item in sections["files"]:
        if item["severity"] == "CRITICAL":
            actions.append((0, 1, f"Chase the sender ({item['sender']}): "
                                  f"**{item['filename']}** never arrived "
                                  f"(due {item['expected_by']}) — the downstream "
                                  f"batch cannot start without it."))
        elif item["severity"] == "WARNING":
            actions.append((1, 1, f"Confirm **{item['filename']}** ({item['detail']}) "
                                  f"with {item['sender']} — check it is complete "
                                  f"before the batch consumes it."))

    for item in sections["certs"]:
        if item["severity"] == "CRITICAL":
            when = "today" if item["days"] == 0 else f"{abs(item['days'])} day(s) ago"
            actions.append((0, 2, f"Renew **{item['service']}** certificate "
                                  f"({item['hostname']}) — it expires {when}. "
                                  f"Owner: {item['owner']}."))
        elif item["severity"] == "WARNING":
            actions.append((1, 2, f"Raise a renewal ticket for **{item['service']}** "
                                  f"({item['hostname']}) — {item['detail']}. "
                                  f"Owner: {item['owner']}."))

    for item in sections["sla"]:
        if item["severity"] == "CRITICAL":
            actions.append((0, 3, f"Escalate **{item['ticket']}** ({item['priority']}, "
                                  f"{item['summary']}) to the duty manager — "
                                  f"{item['detail']}. Owner: {item['owner']}."))
        elif item["severity"] == "WARNING" and "breaches in" in item["detail"]:
            actions.append((1, 3, f"Chase **{item['ticket']}** ({item['priority']}, "
                                  f"{item['summary']}) — {item['detail']}. "
                                  f"Owner: {item['owner']}."))

    for item in sections["disks"]:
        if item["severity"] == "CRITICAL":
            when = ""
            if item["hours_to_full"] is not None:
                eta = as_of + timedelta(hours=item["hours_to_full"])
                when = f" — fills around {eta.strftime('%H:%M')} " \
                       f"({item['hours_to_full']:.1f}h at +{item['growth']}%/h)"
            actions.append((0, 4, f"Clear space on **{item['mount']}** "
                                  f"({item['used']:.0f}% used){when}. "
                                  f"Start with the largest directories (see Day 14) "
                                  f"and the log rotation job (see Day 16)."))
        elif item["severity"] == "WARNING":
            when = ""
            if item["hours_to_full"] is not None:
                eta = as_of + timedelta(hours=item["hours_to_full"])
                when = f" — fills around {eta.strftime('%Y-%m-%d %H:%M')}"
            actions.append((1, 4, f"Plan space on **{item['mount']}** "
                                  f"({item['used']:.0f}% used){when}."))

    actions.sort(key=lambda a: (a[0], a[1]))
    return [text for _, _, text in actions]


# --- Report ----------------------------------------------------------------

def build_report(data, as_of):
    """Run every section check and render the Markdown report.
    Returns (report_text, overall_severity)."""
    sections = {
        "services": check_services(data["services.csv"]),
        "disks": check_disks(data["disks.csv"]),
        "sla": check_sla(data["sla.csv"], as_of),
        "files": check_files(data["files.csv"]),
        "certs": check_certs(data["certs.csv"], as_of),
    }
    section_status = {name: worst_severity(items)
                      for name, items in sections.items()}
    overall = worst_severity(
        [{"severity": s} for s in section_status.values()])
    verdict, _ = VERDICT[overall]
    actions = build_actions(sections, as_of)

    counts = {
        "services_down": sum(1 for i in sections["services"]
                             if i["severity"] == "CRITICAL"),
        "services_degraded": sum(1 for i in sections["services"]
                                 if i["severity"] == "WARNING"),
        "sla_breached": sum(1 for i in sections["sla"]
                            if i["severity"] == "CRITICAL"),
        "sla_at_risk": sum(1 for i in sections["sla"]
                           if i["severity"] == "WARNING"),
        "files_missing": sum(1 for i in sections["files"]
                             if i["severity"] == "CRITICAL"),
        "files_late": sum(1 for i in sections["files"]
                          if i["severity"] == "WARNING"),
        "certs_critical": sum(1 for i in sections["certs"]
                              if i["severity"] == "CRITICAL"),
        "certs_warning": sum(1 for i in sections["certs"]
                             if i["severity"] == "WARNING"),
    }

    lines = [
        "# Daily BAU Health-Check Report",
        "",
        f"**As of:** {as_of.strftime('%Y-%m-%d %H:%M')} · "
        f"**Overall: {verdict}**",
        "",
        "## Summary",
        "",
        "| Area | Status | Headline |",
        "|---|---|---|",
        f"| Services | {STATUS_ICON[section_status['services']]} {section_status['services']} | "
        f"{counts['services_down']} down, {counts['services_degraded']} degraded "
        f"of {len(sections['services'])} |",
        f"| Disk space | {STATUS_ICON[section_status['disks']]} {section_status['disks']} | "
        f"{sum(1 for i in sections['disks'] if i['severity'] == 'CRITICAL')} FAIL, "
        f"{sum(1 for i in sections['disks'] if i['severity'] == 'WARNING')} WARN "
        f"of {len(sections['disks'])} mounts |",
        f"| Incident SLA | {STATUS_ICON[section_status['sla']]} {section_status['sla']} | "
        f"{counts['sla_breached']} breached, {counts['sla_at_risk']} at risk "
        f"of {len(sections['sla'])} open tickets |",
        f"| Files | {STATUS_ICON[section_status['files']]} {section_status['files']} | "
        f"{counts['files_missing']} missing, {counts['files_late']} late "
        f"of {len(sections['files'])} expected |",
        f"| Certificates | {STATUS_ICON[section_status['certs']]} {section_status['certs']} | "
        f"{counts['certs_critical']} critical, {counts['certs_warning']} warning "
        f"of {len(sections['certs'])} |",
        "",
    ]

    if actions:
        lines += ["## Top actions — work these in order", ""]
        for i, action in enumerate(actions, 1):
            lines.append(f"{i}. {action}")
        lines.append("")
    else:
        lines += ["## Top actions", "",
                  "Nothing to do — every area is green. File the report and "
                  "start the day.", ""]

    lines += ["## Services", "",
              "| Service | Status | Latency | Uptime vs SLA | Failed probes | Last error |",
              "|---|---|---|---|---|---|"]
    for i in sections["services"]:
        latency = f"{i['latency']} ms / {i['threshold']} ms" \
            if i["latency"] is not None else "—"
        uptime = f"{i['uptime']:.2f}% vs {i['sla']:.1f}%" \
            if i["uptime"] is not None else "—"
        lines.append(f"| {i['service']} | {STATUS_ICON[i['severity']]} {i['status']} | "
                     f"{latency} | {uptime} | {i['failed']} | "
                     f"{i['last_error'] or '—'} |")
    lines.append("")

    lines += ["## Disk space", "",
              "| Mount | Used | Inodes | Growth | Fills in | Status |",
              "|---|---|---|---|---|---|"]
    for i in sections["disks"]:
        eta = f"{i['hours_to_full']:.1f}h" \
            if i["hours_to_full"] is not None else "—"
        lines.append(f"| {i['mount']} | {i['used']:.0f}% of {i['total_gb']:.0f}G | "
                     f"{i['inodes']:.0f}% | +{i['growth']}%/h | {eta} | "
                     f"{STATUS_ICON[i['severity']]} {i['severity']} |")
    lines.append("")

    lines += ["## Incident SLA (open tickets)", "",
              "| Ticket | Priority | Summary | Status | Owner |",
              "|---|---|---|---|---|"]
    for i in sections["sla"]:
        lines.append(f"| {i['ticket']} | {i['priority']} | {i['summary']} | "
                     f"{STATUS_ICON[i['severity']]} {i['detail']} | {i['owner']} |")
    lines.append("")

    lines += ["## Files expected this morning", "",
              "| File | Due | Arrived | Status |",
              "|---|---|---|---|"]
    for i in sections["files"]:
        lines.append(f"| {i['filename']} | {i['expected_by']} | "
                     f"{i['arrived_at'] or '—'} | "
                     f"{STATUS_ICON[i['severity']]} {i['detail']} |")
    lines.append("")

    lines += ["## Certificates", "",
              "| Hostname | Service | Expires | Status | Owner |",
              "|---|---|---|---|---|"]
    for i in sorted(sections["certs"],
                    key=lambda c: SEVERITY_ORDER.index(c["severity"])):
        lines.append(f"| {i['hostname']} | {i['service']} | "
                     f"{i['expiry'].isoformat()} ({i['detail']}) | "
                     f"{STATUS_ICON[i['severity']]} {i['severity']} | {i['owner']} |")
    lines.append("")

    lines += [
        "## What to do next",
        "",
        "- RED: page the duty manager with this report attached and work "
        "the action list in order — the top item is the one that hurts "
        "the business first.",
        "- AMBER: raise tickets for the warnings and re-run the check "
        "after the 10:00 batch — a warning left alone becomes tomorrow's RED.",
        "- GREEN: file the report; the check still ran, and the record "
        "proves the morning was clean.",
        "- Detail for each area lives in the earlier projects: services "
        "(Day 13), disks (Day 14), SLA (Day 05), files (Day 04), "
        "certificates (Day 15), log cleanup (Day 16).",
        "",
        "*Practice scenario with sample data, built for this portfolio — "
        "not employer work.*",
        "",
    ]
    return "\n".join(lines), overall


def main(argv=None):
    args = parse_args(argv)
    as_of = parse_dt(args.as_of) if args.as_of else datetime.now()
    try:
        data = load_inputs(args.input_dir)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc} — a check that cannot run is not a pass.",
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: cannot read inputs: {exc}", file=sys.stderr)
        return 2

    report, overall = build_report(data, as_of)
    print(report)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)

    return VERDICT[overall][1]


if __name__ == "__main__":
    sys.exit(main())
