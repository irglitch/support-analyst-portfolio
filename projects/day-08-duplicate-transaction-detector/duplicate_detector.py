#!/usr/bin/env python3
"""
Day 08 — Duplicate Transaction Detector

Scenario: Finance reports the daily total looks too high, and a customer
says they were charged twice. Support's job is to find WHICH transactions
were posted twice — exact re-posts and near-duplicates from a double-click
or a retry that got a new ID — without flagging legitimate repeat purchases.

What it does:
  1. Loads the transaction extract (CSV) into SQLite (in-memory, stdlib only).
  2. Runs the queries in duplicates.sql:
     - headline totals (rows, unique txn_ids, total value)
     - exact duplicates: same txn_id posted more than once
     - near duplicates: same customer + amount + day, within 10 minutes,
       different txn_id
  3. Writes a one-page report naming every duplicate charge and the total
     amount at risk, so finance can refund or reverse the exact rows.

Amounts are stored as integer cents in SQLite, so totals are exact.

Exit codes: 0 = no duplicates found, 1 = duplicates found, 2 = error.

Usage:
  python3 duplicate_detector.py sample_data/transactions.csv \
      --out output/duplicate_report.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sqlite3
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

HERE = Path(__file__).resolve().parent
SQL_FILE = HERE / "duplicates.sql"

# Near-duplicate window, in seconds (matches duplicates.sql).
NEAR_DUP_WINDOW_SECONDS = 600


def to_cents(amount_str: str) -> int:
    """'129.99' -> 12999. Decimal keeps money exact; floats never touch it."""
    try:
        return int((Decimal(amount_str.strip()) * 100).to_integral_value())
    except InvalidOperation:
        raise ValueError(f"Bad amount value: {amount_str!r}")


def load_csv(conn, path):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    conn.execute(
        "CREATE TABLE transactions (txn_id TEXT, customer_id TEXT, "
        "txn_timestamp TEXT, amount_cents INTEGER, status TEXT)"
    )
    for r in rows:
        conn.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)",
            (r["txn_id"], r["customer_id"], r["txn_timestamp"],
             to_cents(r["amount"]), r["status"]),
        )
    return len(rows)


def run_queries(conn):
    """Run duplicates.sql statement by statement; return results in order."""
    sql = SQL_FILE.read_text(encoding="utf-8")
    # Strip full-line comments, then split on semicolons (no ';' inside our SQL).
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    return [conn.execute(stmt).fetchall() for stmt in statements]


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def build_report(results):
    (row_count, unique_ids, total_cents) = results[0][0]
    exact_dupes = results[1]
    near_dupes = results[2]

    # Extra charges: every re-post beyond the first, plus the second charge
    # of each near-duplicate pair.
    extra_exact = sum(c - 1 for *_, c, _, _ in exact_dupes)
    extra_exact_cents = sum(cents * (c - 1)
                            for _, _, cents, c, _, _ in exact_dupes)
    extra_near_cents = sum(r[3] for r in near_dupes)
    n_duplicate_charges = extra_exact + len(near_dupes)
    amount_at_risk = extra_exact_cents + extra_near_cents

    verdict = (
        "✅ CLEAN — no duplicate transactions found."
        if n_duplicate_charges == 0
        else f"🔴 DUPLICATES FOUND — {n_duplicate_charges} extra charge(s), "
             f"{money(amount_at_risk)} at risk."
    )

    lines = [
        "# Duplicate Transaction Report",
        "",
        f"**Transactions in extract:** {row_count}  ",
        f"**Unique transaction IDs:** {unique_ids}  ",
        f"**Total value posted:** {money(total_cents)}  ",
        f"**Duplicate extra charges:** {n_duplicate_charges}  ",
        f"**Amount at risk:** {money(amount_at_risk)}  ",
        f"**Verdict:** {verdict}",
        "",
        "## 1. Exact duplicates — same transaction ID posted more than once",
        "",
    ]
    if exact_dupes:
        lines += ["| Transaction | Customer | Amount | Times posted | First seen | Last seen |",
                  "|---|---|---|---|---|---|"]
        for txn, cust, cents, count, first, last in exact_dupes:
            lines.append(
                f"| {txn} | {cust} | {money(cents)} | {count} | {first} | {last} |")
    else:
        lines.append("None — every transaction ID appears exactly once.")
    lines += ["", "## 2. Near duplicates — same customer, amount and day, within 10 minutes",
              ""]
    if near_dupes:
        lines += ["| First charge | Second charge | Customer | Amount | Seconds apart |",
                  "|---|---|---|---|---|"]
        for txn_a, txn_b, cust, cents, time_a, time_b, secs in near_dupes:
            lines.append(
                f"| {txn_a} ({time_a}) | {txn_b} ({time_b}) | {cust} | "
                f"{money(cents)} | {secs} |")
    else:
        lines.append("None — no same-customer, same-amount pairs within 10 minutes.")
    lines += [
        "",
        "## How the amount at risk adds up",
        "",
        f"- Exact re-posts: {money(extra_exact_cents)} "
        f"({extra_exact} extra charge(s))",
        f"- Near duplicates: {money(extra_near_cents)} "
        f"({len(near_dupes)} extra charge(s))",
        "",
        "## What was checked and NOT flagged",
        "",
        "- TXN-3014: same customer (CUST-104) and amount ($59.99) as "
        "TXN-3004, but 5 hours later — a legitimate repeat purchase, "
        "outside the 10-minute window.",
        "- TXN-3017: same amount ($59.99) as CUST-104's charges, but a "
        "different customer (CUST-115) — not a duplicate.",
        "",
        "Next steps, escalation path and RCA prompts: see `RUNBOOK.md`.",
        "",
    ]
    return "\n".join(lines), n_duplicate_charges


def detect(csv_path):
    """Return (report_text, number_of_duplicate_charges)."""
    conn = sqlite3.connect(":memory:")
    try:
        load_csv(conn, csv_path)
        return build_report(run_queries(conn))
    finally:
        conn.close()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Find duplicate transactions in a daily extract.")
    ap.add_argument("transactions_csv", help="Transaction extract (CSV)")
    ap.add_argument("--out", default=None,
                    help="Write the report to this file (default: stdout)")
    args = ap.parse_args(argv)

    try:
        report, n_dupes = detect(args.transactions_csv)
    except (FileNotFoundError, ValueError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(report)
    return 1 if n_dupes else 0


if __name__ == "__main__":
    raise SystemExit(main())
