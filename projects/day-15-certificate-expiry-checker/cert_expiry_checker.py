#!/usr/bin/env python3
"""Certificate Expiry Checker — Day 15 of the support analyst portfolio.

Scenario: a TLS certificate that expires unnoticed takes a service down
with no warning — users see "connection not secure" or the integration
simply stops working. Support keeps a certificate inventory (CSV) and
this tool checks every entry against WARN / CRITICAL thresholds, so
renewals are raised as tickets *before* anything breaks.

Usage:
    python3 cert_expiry_checker.py sample_data/certificates.csv
    python3 cert_expiry_checker.py sample_data/certificates.csv --as-of 2026-11-21 \\
        --out output/certificate_expiry_report.md

    # Optionally check one live host as well (stdlib ssl, needs network):
    python3 cert_expiry_checker.py --host api.example.com

Exit codes (so a scheduler can alert on them):
    0  all certificates OK
    1  at least one WARNING, nothing worse
    2  at least one CRITICAL or EXPIRED

Python standard library only.
"""

import argparse
import csv
import socket
import ssl
import sys
from datetime import date, datetime
from pathlib import Path

WARN_DAYS = 30    # 30 days or fewer: raise a renewal ticket now
CRIT_DAYS = 14    # 14 days or fewer: urgent — renewal must be scheduled this week

STATUS_ORDER = ["EXPIRED", "CRITICAL", "WARNING", "OK"]
STATUS_ICON = {"EXPIRED": "🔴", "CRITICAL": "🔴", "WARNING": "🟡", "OK": "🟢"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Check certificate expiry dates.")
    parser.add_argument("inventory", nargs="?", default=None,
                        help="CSV inventory file (hostname,service,environment,"
                             "issuer,expiry_date,owner)")
    parser.add_argument("--as-of", default=None,
                        help="Reference date YYYY-MM-DD (default: today). "
                             "Use it to reproduce a report.")
    parser.add_argument("--warn-days", type=int, default=WARN_DAYS)
    parser.add_argument("--crit-days", type=int, default=CRIT_DAYS)
    parser.add_argument("--out", default=None, help="Write the report to this file")
    parser.add_argument("--host", default=None,
                        help="Also check the live certificate of this host")
    return parser.parse_args(argv)


def parse_date(value):
    """Accept YYYY-MM-DD (and a full ISO datetime, taking its date part)."""
    value = value.strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return datetime.fromisoformat(value).date()


def load_inventory(path):
    """Read the certificate inventory CSV. Returns a list of dicts."""
    certs = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            certs.append({
                "hostname": row["hostname"].strip(),
                "service": row["service"].strip(),
                "environment": row["environment"].strip(),
                "issuer": row["issuer"].strip(),
                "expiry_date": parse_date(row["expiry_date"]),
                "owner": row["owner"].strip(),
            })
    return certs


def days_remaining(cert, as_of):
    """Whole days from the reference date until the certificate expires."""
    return (cert["expiry_date"] - as_of).days


def classify(days, warn_days=WARN_DAYS, crit_days=CRIT_DAYS):
    """Expiry status from days remaining."""
    if days < 0:
        return "EXPIRED"
    if days <= crit_days:
        return "CRITICAL"
    if days <= warn_days:
        return "WARNING"
    return "OK"


def check_host_certificate(hostname, port=443, timeout=10):
    """Fetch the live certificate of a host and return its expiry date.

    Returns None if the host cannot be reached (network errors are
    reported, not hidden — a check that cannot run is not a pass).
    """
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                peer = ssock.getpeercert()
    except (socket.error, ssl.SSLError, OSError) as exc:
        return None, str(exc)
    not_after = datetime.strptime(peer["notAfter"],
                                  "%b %d %H:%M:%S %Y %Z").date()
    return not_after, None


def build_report(certs, as_of, warn_days=WARN_DAYS, crit_days=CRIT_DAYS,
                 live_check=None):
    """Build the Markdown expiry report. Returns (report_text, worst_status)."""
    rows = []
    for cert in certs:
        days = days_remaining(cert, as_of)
        rows.append({**cert, "days": days,
                     "status": classify(days, warn_days, crit_days)})
    rows.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), r["days"]))

    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER}
    worst = next((s for s in STATUS_ORDER if counts[s] > 0), "OK")

    lines = [
        "# Certificate Expiry Report",
        "",
        f"Checked: {len(certs)} certificate(s) · Reference date: {as_of.isoformat()}",
        f"Thresholds: WARNING ≤ {warn_days} days · CRITICAL ≤ {crit_days} days",
        "",
        "## Summary",
        "",
        f"- 🔴 EXPIRED: **{counts['EXPIRED']}**",
        f"- 🔴 CRITICAL (≤ {crit_days} days): **{counts['CRITICAL']}**",
        f"- 🟡 WARNING (≤ {warn_days} days): **{counts['WARNING']}**",
        f"- 🟢 OK: **{counts['OK']}**",
        "",
        f"**Overall: {STATUS_ICON[worst]} {worst}**",
        "",
    ]

    action = [r for r in rows if r["status"] != "OK"]
    if action:
        lines += ["## Needs action", "",
                  "| Hostname | Service | Environment | Expires | Days left | Status | Owner |",
                  "|---|---|---|---|---|---|---|"]
        for r in action:
            lines.append(
                f"| {r['hostname']} | {r['service']} | {r['environment']} | "
                f"{r['expiry_date'].isoformat()} | {r['days']} | "
                f"{STATUS_ICON[r['status']]} {r['status']} | {r['owner']} |")
        lines.append("")

    healthy = [r for r in rows if r["status"] == "OK"]
    if healthy:
        lines += ["## OK — no action needed", "",
                  "| Hostname | Service | Expires | Days left | Owner |",
                  "|---|---|---|---|---|"]
        for r in healthy:
            lines.append(
                f"| {r['hostname']} | {r['service']} | "
                f"{r['expiry_date'].isoformat()} | {r['days']} | {r['owner']} |")
        lines.append("")

    if live_check:
        host, expiry, error = live_check
        lines += ["## Live host check", ""]
        if error:
            lines.append(f"- {host}: **could not be checked** — {error}")
        else:
            days = (expiry - as_of).days
            status = classify(days, warn_days, crit_days)
            lines.append(f"- {host}: expires {expiry.isoformat()} "
                         f"({days} days) — {STATUS_ICON[status]} {status}")
        lines.append("")

    lines += [
        "## What to do next",
        "",
        "- EXPIRED: treat as an incident — the service is already failing "
        "for anyone validating the certificate. Escalate to the certificate "
        "owner immediately.",
        "- CRITICAL: raise the renewal ticket today and confirm the renewal "
        "date with the owner. If it expires over a weekend, act before Friday.",
        "- WARNING: raise the renewal ticket and add the expiry to the "
        "team calendar.",
        "",
        "*Practice scenario with sample data, built for this portfolio — "
        "not employer work.*",
        "",
    ]
    return "\n".join(lines), worst


def main(argv=None):
    args = parse_args(argv)
    as_of = parse_date(args.as_of) if args.as_of else date.today()

    certs = []
    if args.inventory:
        certs = load_inventory(args.inventory)

    live_check = None
    if args.host:
        expiry, error = check_host_certificate(args.host)
        live_check = (args.host, expiry, error)

    if not certs and not live_check:
        print("No inventory file and no --host given.", file=sys.stderr)
        return 2

    report, worst = build_report(certs, as_of, args.warn_days, args.crit_days,
                                 live_check)
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report)

    return {"OK": 0, "WARNING": 1, "CRITICAL": 2, "EXPIRED": 2}[worst]


if __name__ == "__main__":
    sys.exit(main())
