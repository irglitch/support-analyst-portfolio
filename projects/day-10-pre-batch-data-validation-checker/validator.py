#!/usr/bin/env python3
"""
Day 10 — Pre-Batch Data Validation Checker

Scenario: Monday, 09:20. The overnight settlement batch (batch 8815) is
due to run at 10:00, and Finance has just dropped the staging file.
Support's job is to validate the file BEFORE the batch runs — a bad row
inside the batch means a failed run, a partial settlement and a 10 a.m.
incident. Catch the bad rows now, send them back to Finance with named
transaction IDs, and let the batch run on clean data only.

What it does:
  1. Loads the staging CSV into SQLite (in-memory, stdlib only).
  2. Runs the checks in validation.sql:
     - duplicate transaction IDs
     - missing, negative or zero amounts
     - unexpected currency (this batch settles CAD and USD only)
     - transaction dates after the batch date
     - malformed account numbers (must be ACC- + 4 digits)
     - missing customer IDs
     - invalid status (only settled / pending may enter the batch)
  3. Writes a one-page report: verdict (GO / BLOCKED), the count of
     valid vs blocked rows, the valid-row total, and every bad row
     named by transaction ID so Finance can fix exactly those rows.

The tool only reads the staging file and reports — it never edits the
file, never deletes a row and never starts the batch. Whether the batch
runs with the bad rows removed, or waits for a corrected file, is
Finance's call; support supplies the evidence.

Exit codes: 0 = GO (no blockers), 1 = BLOCKED (bad rows found),
2 = error (file missing / unreadable / wrong shape).

Usage:
  python3 validator.py sample_data/staging_settlements.csv \\
      --batch-date 2026-11-16 --out output/validation_report.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "validation.sql"

BATCH_DATE = "2026-11-16"
ALLOWED_CURRENCIES = ("CAD", "USD")
ALLOWED_STATUSES = ("settled", "pending")
COLUMNS = ["txn_id", "customer_id", "amount", "currency",
           "txn_date", "account_no", "status"]

# rule label -> SQL that returns the offending txn_ids
CHECKS = [
    ("Duplicate transaction ID",
     "SELECT txn_id FROM staging GROUP BY txn_id HAVING COUNT(*) > 1"),
    ("Missing amount",
     "SELECT txn_id FROM staging WHERE amount IS NULL OR TRIM(amount) = ''"),
    ("Negative amount",
     "SELECT txn_id FROM staging WHERE amount IS NOT NULL AND TRIM(amount) <> '' "
     "AND CAST(amount AS REAL) < 0"),
    ("Zero amount",
     "SELECT txn_id FROM staging WHERE amount IS NOT NULL AND TRIM(amount) <> '' "
     "AND CAST(amount AS REAL) = 0"),
    ("Unexpected currency (batch settles CAD / USD only)",
     "SELECT txn_id FROM staging WHERE currency NOT IN ('CAD', 'USD')"),
    ("Future transaction date (after batch date)",
     "SELECT txn_id FROM staging WHERE txn_date > ?"),
    ("Malformed account number (must be ACC- + 4 digits)",
     "SELECT txn_id FROM staging WHERE account_no NOT GLOB 'ACC-[0-9][0-9][0-9][0-9]'"),
    ("Missing customer ID",
     "SELECT txn_id FROM staging WHERE customer_id IS NULL OR TRIM(customer_id) = ''"),
    ("Invalid status (only settled / pending may enter the batch)",
     "SELECT txn_id FROM staging WHERE status NOT IN ('settled', 'pending')"),
]


def _fmt_amount(value):
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def check(csv_path, batch_date=BATCH_DATE):
    """Validate a staging CSV. Returns (report_markdown, n_blocked_rows)."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"staging file not found: {csv_path}")

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != COLUMNS:
            raise ValueError(
                f"unexpected header {reader.fieldnames!r}, expected {COLUMNS!r}")
        rows = list(reader)

    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE staging ("
        "txn_id TEXT, customer_id TEXT, amount TEXT, currency TEXT, "
        "txn_date TEXT, account_no TEXT, status TEXT)")
    conn.executemany(
        "INSERT INTO staging VALUES (?,?,?,?,?,?,?)",
        [[r.get(c, "") for c in COLUMNS] for r in rows])

    # Map txn_id -> row positions (1-based, in file order) so a duplicated
    # ID flags both of its rows.
    positions = {}
    for i, row in enumerate(rows, start=1):
        positions.setdefault(row["txn_id"], []).append(i)

    blocked_rows = set()
    findings = []  # (label, [txn_ids])
    for label, sql in CHECKS:
        params = (batch_date,) if "?" in sql else ()
        txn_ids = [r[0] for r in conn.execute(sql, params)]
        if txn_ids:
            findings.append((label, txn_ids))
            for txn_id in txn_ids:
                blocked_rows.update(positions.get(txn_id, []))
    conn.close()

    total = len(rows)
    n_blocked = len(blocked_rows)
    n_valid = total - n_blocked
    valid_total = sum(
        float(r["amount"]) for i, r in enumerate(rows, start=1)
        if i not in blocked_rows and r["amount"].strip() != "")
    verdict = "🟢 GO — batch may run" if n_blocked == 0 else "🔴 BLOCKED — do not run the batch"

    lines = [
        "# Pre-Batch Data Validation — Batch 8815",
        "",
        f"**Batch date:** {batch_date}  ·  **Staging file:** {path.name}",
        "",
        f"## Verdict: {verdict}",
        "",
        f"- **Rows in file:** {total}",
        f"- **Valid rows:** {n_valid} (total {_fmt_amount(valid_total)})",
        f"- **Blocked rows:** {n_blocked}",
        f"- **Rules failed:** {len(findings)} of {len(CHECKS)}",
        "",
    ]
    if findings:
        lines.append("## Bad rows — send these back to Finance")
        lines.append("")
        for label, txn_ids in findings:
            n_rows = sum(len(positions.get(t, [])) for t in txn_ids)
            lines.append(f"- **{label}:** {', '.join(txn_ids)} "
                         f"({n_rows} row{'s' if n_rows != 1 else ''})")
        lines.append("")
        lines.append("Fix the rows above and re-validate before the 10:00 run. "
                     "Do not run the batch on the file as it stands — a "
                     "duplicate transaction ID would settle the same payment "
                     "twice, and a missing or negative amount would fail the "
                     "batch mid-run.")
    else:
        lines.append("No problems found — every row passed all checks.")
    lines.append("")
    return "\n".join(lines), n_blocked


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate a settlement staging file before the batch runs.")
    parser.add_argument("csv_file", help="staging CSV to validate")
    parser.add_argument("--batch-date", default=BATCH_DATE,
                        help="batch date, YYYY-MM-DD (default %(default)s)")
    parser.add_argument("--out", help="write the report to this file")
    args = parser.parse_args(argv)

    try:
        report, n_blocked = check(args.csv_file, args.batch_date)
    except (FileNotFoundError, ValueError, csv.Error, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    print(report)
    return 1 if n_blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
