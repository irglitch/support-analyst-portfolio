#!/usr/bin/env python3
"""
Day 04 — File Transfer Monitor

Scenario: Every morning the business expects a set of files to arrive by a
fixed time — the 7 AM settlement file from the payment processor, a CRM
feed, FX rates, an audit log. If one is missing, late, or empty (a failed
transfer), the downstream batch and finance reconciliation are blocked.
Support's job is to spot the gap before the business calls asking where
the numbers are.

What this tool does:
  1. Reads the expected-files manifest (filename, expected-by time, source,
     minimum size, whether it is critical, business impact).
  2. Reads the transfer log for the morning (filename, received time, size)
     — the log a support analyst would get from the SFTP / transfer system.
  3. Optionally verifies each received file against the real drop folder
     (--drop-dir): a file in the log but not on disk, or a size that does
     not match the log, is flagged.
  4. Reports per file: OK / LATE / MISSING / EMPTY / SMALL, with an overall
     status and an exit code monitoring can use:
       0 = all files OK, 1 = warning (late or undersized), 2 = alert
       (missing or empty file).

Usage:
  python3 file_transfer_monitor.py sample_data/expected_files.csv \\
      sample_data/transfer_log_20261110.csv --now 07:30 \\
      --drop-dir sample_data/incoming --out output/transfer_status_report.md

No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# Exit codes — monitoring-friendly
EXIT_OK = 0
EXIT_WARNING = 1
EXIT_ALERT = 2


def parse_hhmm(value):
    """Parse 'HH:MM' into a time object; raise ValueError on bad input."""
    return datetime.strptime(value.strip(), "%H:%M").time()


def load_manifest(path):
    """Return a list of expected-file dicts from the manifest CSV."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    expected = []
    for row in rows:
        expected.append({
            "filename": row["filename"].strip(),
            "expected_by": parse_hhmm(row["expected_by"]),
            "expected_by_raw": row["expected_by"].strip(),
            "source": row["source"].strip(),
            "min_size_bytes": int(row["min_size_bytes"]),
            "critical": row["critical"].strip().lower() in ("yes", "true", "y", "1"),
            "business_impact": row["business_impact"].strip(),
        })
    return expected


def load_transfer_log(path):
    """Return {filename: {"received_at": time, "size_bytes": int}}."""
    received = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            received[row["filename"].strip()] = {
                "received_at": parse_hhmm(row["received_at"]),
                "received_at_raw": row["received_at"].strip(),
                "size_bytes": int(row["size_bytes"]),
            }
    return received


def check_transfers(manifest, received, now, drop_dir=None):
    """Check every expected file. Returns (results, unexpected_files).

    Each result: filename, status, received_at, size_bytes, expected_by,
    source, critical, business_impact, note.
    Status: OK / LATE / MISSING / EMPTY / SMALL.
    """
    results = []
    for item in manifest:
        name = item["filename"]
        rec = received.get(name)
        result = {
            "filename": name,
            "expected_by": item["expected_by_raw"],
            "source": item["source"],
            "critical": item["critical"],
            "business_impact": item["business_impact"],
            "received_at": rec["received_at_raw"] if rec else "—",
            "size_bytes": rec["size_bytes"] if rec else None,
            "status": None,
            "note": "",
        }
        if rec is None:
            result["status"] = "MISSING"
            result["note"] = "No arrival recorded in the transfer log"
        else:
            disk = None
            if drop_dir is not None:
                disk_path = Path(drop_dir) / name
                if not disk_path.exists():
                    result["status"] = "MISSING"
                    result["note"] = "In the transfer log but NOT on disk — transfer did not land"
                    results.append(result)
                    continue
                disk = disk_path.stat().st_size
                if disk != rec["size_bytes"]:
                    result["note"] = (
                        f"Size on disk ({disk} B) differs from transfer log "
                        f"({rec['size_bytes']} B) — partial or replaced transfer?"
                    )
            size = disk if disk is not None else rec["size_bytes"]
            result["size_bytes"] = size
            if size == 0:
                result["status"] = "EMPTY"
                result["note"] = "Zero-byte file — transfer failed or source sent nothing"
            elif size < item["min_size_bytes"]:
                result["status"] = "SMALL"
                result["note"] = (
                    f"Only {size} B, expected at least {item['min_size_bytes']} B "
                    "— likely a truncated / partial transfer"
                )
            elif rec["received_at"] > item["expected_by"]:
                result["status"] = "LATE"
                result["note"] = (
                    f"Arrived {rec['received_at_raw']}, "
                    f"{item['expected_by_raw']} was the deadline"
                )
            else:
                result["status"] = "OK"
                result["note"] = "On time and complete"
        results.append(result)

    unexpected = sorted(set(received) - {item["filename"] for item in manifest})
    return results, unexpected


def overall_status(results):
    """Return (status_label, exit_code, summary_line)."""
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    missing = [r for r in results if r["status"] in ("MISSING", "EMPTY")]
    if missing:
        critical = [r["filename"] for r in missing if r["critical"]]
        label = "🔴 ALERT"
        detail = f"{len(missing)} file(s) missing or empty"
        if critical:
            detail += f" — including CRITICAL: {', '.join(critical)}"
        return label, EXIT_ALERT, detail
    if counts.get("LATE") or counts.get("SMALL"):
        return ("🟡 WARNING", EXIT_WARNING,
                f"{counts.get('LATE', 0)} late, {counts.get('SMALL', 0)} undersized")
    return "🟢 OK", EXIT_OK, "All expected files arrived on time and complete"


def build_report(results, unexpected, now_raw, manifest_name):
    status_label, _, detail = overall_status(results)
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines = [
        "# File Transfer Status Report",
        "",
        f"**Manifest:** `{manifest_name}`  ",
        f"**Checked at:** {now_raw}  ",
        f"**Overall status:** {status_label} — {detail}  ",
        f"**Files checked:** {len(results)} · "
        f"OK {counts.get('OK', 0)} · LATE {counts.get('LATE', 0)} · "
        f"MISSING {counts.get('MISSING', 0)} · EMPTY {counts.get('EMPTY', 0)} · "
        f"SMALL {counts.get('SMALL', 0)}",
        "",
        "## Expected files",
        "",
        "| File | Expected by | Received | Size | Status | Source |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        size = f"{r['size_bytes']} B" if r["size_bytes"] is not None else "—"
        lines.append(
            f"| `{r['filename']}` | {r['expected_by']} | {r['received_at']} | "
            f"{size} | **{r['status']}** | {r['source']} |"
        )
    lines += ["", "## What needs action", ""]
    problems = [r for r in results if r["status"] != "OK"]
    if not problems:
        lines.append("Nothing outstanding — all files arrived on time and complete.")
    for r in problems:
        crit = " (CRITICAL)" if r["critical"] else ""
        lines.append(f"- **{r['status']}** — `{r['filename']}`{crit}: {r['note']}.")
        lines.append(f"  Impact: {r['business_impact']}")
    if unexpected:
        lines += ["", "## Unexpected files (arrived but not in the manifest)", ""]
        for name in unexpected:
            lines.append(
                f"- `{name}` — confirm with the sender whether this is a new "
                "feed to add to the manifest or a misdirected file."
            )
    lines += [
        "",
        "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check this morning's expected file transfers against the manifest.")
    ap.add_argument("manifest", help="Expected-files manifest CSV")
    ap.add_argument("transfer_log", help="Transfer log CSV for the morning")
    ap.add_argument("--now", default=None,
                    help="Check time as HH:MM (default: current local time)")
    ap.add_argument("--drop-dir", default=None,
                    help="Drop folder to verify received files against on disk")
    ap.add_argument("--out", default=None,
                    help="Write the report to this file (default: stdout)")
    args = ap.parse_args(argv)

    now_raw = args.now or datetime.now().strftime("%H:%M")
    try:
        now = parse_hhmm(now_raw)
    except ValueError:
        print(f"--now must be HH:MM, got {now_raw!r}", file=sys.stderr)
        return 2

    manifest = load_manifest(args.manifest)
    received = load_transfer_log(args.transfer_log)
    results, unexpected = check_transfers(manifest, received, now, args.drop_dir)
    report = build_report(results, unexpected, now_raw, Path(args.manifest).name)
    status_label, exit_code, detail = overall_status(results)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    print(f"{status_label} — {detail} (exit {exit_code})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
