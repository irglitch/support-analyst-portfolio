#!/usr/bin/env python3
"""
Day 03 — SQL Reconciliation Break Finder

Scenario: Finance reports the daily totals don't match — the billing system
says one number, the finance ledger says another. Support's job is to find
WHICH transactions break, not just that the totals differ.

What it does:
  1. Loads the two CSV extracts into SQLite (in-memory, stdlib only).
  2. Runs the queries in reconciliation.sql:
     - totals + counts per system
     - billed but never posted (missing from ledger)
     - posted but never billed (orphan in ledger)
     - same transaction, different amount
     - matched and agreeing (sanity check)
  3. Writes a one-page reconciliation report naming every break, so finance
     can chase the exact transactions instead of re-checking the whole day.

Amounts are stored as integer cents in SQLite, so totals are exact.

Usage:
  python3 recon_break_finder.py sample_data/billing_extract.csv \
      sample_data/finance_ledger.csv --out output/reconciliation_report.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sqlite3
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "reconciliation.sql"


def to_cents(amount_str: str) -> int:
    """'210.00' -> 21000. Decimal keeps money exact; floats never touch it."""
    try:
        return int((Decimal(amount_str.strip()) * 100).to_integral_value())
    except InvalidOperation:
        raise ValueError(f"Bad amount value: {amount_str!r}")


def load_csv(conn, table, path, date_col):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    conn.execute(
        f"CREATE TABLE {table} (txn_id TEXT PRIMARY KEY, customer_id TEXT, "
        f"{date_col} TEXT, amount_cents INTEGER, status TEXT)"
    )
    for r in rows:
        conn.execute(
            f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?)",
            (r["txn_id"], r["customer_id"], r[date_col],
             to_cents(r["amount"]), r["status"]),
        )
    return len(rows)


def run_queries(conn):
    """Run reconciliation.sql statement by statement; return results in order."""
    sql = SQL_FILE.read_text(encoding="utf-8")
    # Strip full-line comments, then split on semicolons (no ';' inside our SQL).
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    return [conn.execute(stmt).fetchall() for stmt in statements]


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def build_report(results):
    (billing_total,) = results[0]
    (ledger_total,) = results[1]
    missing_in_ledger = results[2]
    orphan_in_ledger = results[3]
    amount_mismatches = results[4]
    (matched_agreeing,) = results[5]

    _, b_count, b_total = billing_total
    _, l_count, l_total = ledger_total
    diff = b_total - l_total
    n_breaks = len(missing_in_ledger) + len(orphan_in_ledger) + len(amount_mismatches)

    verdict = (
        "✅ RECONCILED — totals and transactions agree."
        if diff == 0 and n_breaks == 0
        else f"❌ BREAK FOUND — {n_breaks} transaction(s) explain a {money(diff)} difference."
    )

    lines = [
        "# Reconciliation Report — Billing vs Finance Ledger",
        "",
        f"**Billing system:** {b_count} transactions, total **{money(b_total)}**  ",
        f"**Finance ledger:** {l_count} transactions, total **{money(l_total)}**  ",
        f"**Difference (billing − ledger):** {money(diff)}  ",
        f"**Transactions matched and agreeing:** {matched_agreeing[0]}  ",
        f"**Verdict:** {verdict}",
        "",
        "## 1. Billed but never posted (missing from ledger)",
        "",
    ]
    if missing_in_ledger:
        lines += ["| Transaction | Customer | Date | Amount |",
                  "|---|---|---|---|"]
        for txn, cust, date, cents in missing_in_ledger:
            lines.append(f"| {txn} | {cust} | {date} | {money(cents)} |")
    else:
        lines.append("None — every billed transaction reached the ledger.")
    lines += ["", "## 2. Posted but never billed (orphan in ledger)", ""]
    if orphan_in_ledger:
        lines += ["| Transaction | Customer | Date | Amount |",
                  "|---|---|---|---|"]
        for txn, cust, date, cents in orphan_in_ledger:
            lines.append(f"| {txn} | {cust} | {date} | {money(cents)} |")
    else:
        lines.append("None — every ledger posting has a matching bill.")
    lines += ["", "## 3. Same transaction, different amount", ""]
    if amount_mismatches:
        lines += ["| Transaction | Billing | Ledger | Difference (ledger − billing) |",
                  "|---|---|---|---|"]
        for txn, b_cents, l_cents, d_cents in amount_mismatches:
            lines.append(f"| {txn} | {money(b_cents)} | {money(l_cents)} | {money(d_cents)} |")
    else:
        lines.append("None — every matched transaction agrees on the amount.")
    lines += [
        "", "## How the difference adds up",
        "",
        f"- Missing from ledger: {money(sum(r[3] for r in missing_in_ledger))} "
        f"({len(missing_in_ledger)} transaction(s))",
        f"- Orphan in ledger: {money(-sum(r[3] for r in orphan_in_ledger))} "
        f"({len(orphan_in_ledger)} transaction(s))",
        f"- Amount mismatches: {money(-sum(r[3] for r in amount_mismatches))} "
        f"({len(amount_mismatches)} transaction(s))",
        "",
        "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.",
        "",
    ]
    return "\n".join(lines)


def reconcile(billing_csv, ledger_csv):
    conn = sqlite3.connect(":memory:")
    try:
        load_csv(conn, "billing", billing_csv, "txn_date")
        load_csv(conn, "finance_ledger", ledger_csv, "posting_date")
        return build_report(run_queries(conn))
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Find reconciliation breaks between a billing extract and a finance ledger.")
    ap.add_argument("billing_csv", help="Billing system extract (CSV)")
    ap.add_argument("ledger_csv", help="Finance ledger extract (CSV)")
    ap.add_argument("--out", default=None, help="Write the report to this file (default: stdout)")
    args = ap.parse_args(argv)

    try:
        report = reconcile(args.billing_csv, args.ledger_csv)
    except (FileNotFoundError, ValueError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
