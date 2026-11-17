#!/usr/bin/env python3
"""
Day 11 — Reconciliation Summary Report Generator

Scenario: Tuesday, 09:20. The overnight settlement batch has run and
Finance wants the daily reconciliation summary before the 10:00 close
call: do the source system and the ledger agree on yesterday's
settlements? Manually comparing two files row by row is slow and the
one row that doesn't match is exactly the one you miss. This tool
compares the two settlement files on transaction ID and produces a
one-page summary Finance can act on: matched vs broken, totals per
system, the net difference, and every break named by transaction ID
with its type and amount.

What it does:
  1. Loads both CSVs (source system and ledger) — stdlib only.
  2. Matches rows on txn_id and classifies each transaction:
     - matched exactly (same amount and currency)
     - amount mismatch (same txn_id, different amount or currency)
     - missing in ledger (in source only — never posted)
     - missing in source (in ledger only — posted but no source record)
  3. Totals each file, computes the net difference (ledger - source),
     the total value of all breaks, and the single largest break.
  4. Writes a one-page Markdown report with a verdict:
     RECONCILED (no breaks) or BREAKS FOUND.

Amounts use Decimal, not float, so the totals add up exactly — a
reconciliation report whose own numbers don't balance is worse than
no report.

The tool only reads the two files and reports — it never edits either
file and never posts a correcting entry. Fixing a break (re-post,
reverse, or write-off) is Finance's call; support supplies the
evidence.

Exit codes: 0 = RECONCILED (no breaks), 1 = BREAKS FOUND,
2 = error (file missing / unreadable / wrong shape).

Usage:
  python3 reconcile_report.py sample_data/source_settlements.csv \\
      sample_data/ledger_settlements.csv --out output/reconciliation_summary.md
No external dependencies. Python 3.9+.
"""
import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = ["txn_id", "customer_id", "amount", "currency",
           "txn_date", "account_no", "status"]


def load_csv(path):
    """Load a settlement CSV into {txn_id: row}. Raises ValueError on bad input."""
    rows = {}
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or "txn_id" not in reader.fieldnames \
                    or "amount" not in reader.fieldnames:
                raise ValueError(f"{path}: expected columns txn_id, amount, ...")
            for line_no, row in enumerate(reader, start=2):
                txn_id = (row.get("txn_id") or "").strip()
                if not txn_id:
                    raise ValueError(f"{path} line {line_no}: missing txn_id")
                if txn_id in rows:
                    raise ValueError(
                        f"{path} line {line_no}: duplicate txn_id {txn_id}")
                try:
                    amount = Decimal((row.get("amount") or "").strip())
                except InvalidOperation:
                    raise ValueError(
                        f"{path} line {line_no}: bad amount "
                        f"'{row.get('amount')}' for {txn_id}")
                rows[txn_id] = {
                    "txn_id": txn_id,
                    "amount": amount,
                    "currency": (row.get("currency") or "").strip(),
                    "customer_id": (row.get("customer_id") or "").strip(),
                }
    except FileNotFoundError:
        raise ValueError(f"file not found: {path}")
    return rows


def reconcile(source, ledger):
    """Compare two {txn_id: row} dicts. Returns a summary dict."""
    matched = []
    amount_mismatch = []   # (txn_id, source amount, ledger amount, diff)
    missing_in_ledger = []  # (txn_id, amount)
    missing_in_source = []  # (txn_id, amount)

    for txn_id, s_row in source.items():
        l_row = ledger.get(txn_id)
        if l_row is None:
            missing_in_ledger.append((txn_id, s_row["amount"]))
        elif s_row["amount"] != l_row["amount"] \
                or s_row["currency"] != l_row["currency"]:
            amount_mismatch.append(
                (txn_id, s_row["amount"], l_row["amount"],
                 l_row["amount"] - s_row["amount"]))
        else:
            matched.append(txn_id)

    for txn_id, l_row in ledger.items():
        if txn_id not in source:
            missing_in_source.append((txn_id, l_row["amount"]))

    source_total = sum((r["amount"] for r in source.values()), Decimal("0"))
    ledger_total = sum((r["amount"] for r in ledger.values()), Decimal("0"))
    net_difference = ledger_total - source_total

    break_values = [abs(d) for _, _, _, d in amount_mismatch] \
        + [a for _, a in missing_in_ledger] \
        + [a for _, a in missing_in_source]
    total_break_value = sum(break_values, Decimal("0"))

    largest = None
    candidates = [(f"Amount mismatch {t}", abs(d))
                  for t, _, _, d in amount_mismatch] \
        + [(f"Missing in ledger {t}", a) for t, a in missing_in_ledger] \
        + [(f"Missing in source {t}", a) for t, a in missing_in_source]
    if candidates:
        largest = max(candidates, key=lambda c: c[1])

    return {
        "source_rows": len(source),
        "ledger_rows": len(ledger),
        "matched": len(matched),
        "amount_mismatch": amount_mismatch,
        "missing_in_ledger": missing_in_ledger,
        "missing_in_source": missing_in_source,
        "break_count": len(amount_mismatch) + len(missing_in_ledger)
                       + len(missing_in_source),
        "source_total": source_total,
        "ledger_total": ledger_total,
        "net_difference": net_difference,
        "total_break_value": total_break_value,
        "largest_break": largest,
    }


def money(value):
    return f"${value:,.2f}"


def render_report(summary, source_name, ledger_name, recon_date):
    lines = [
        f"# Daily Reconciliation Summary — {recon_date}",
        "",
        f"**Source file:** {source_name}  ·  **Ledger file:** {ledger_name}",
        "",
    ]
    if summary["break_count"] == 0:
        lines.append("## Verdict: 🟢 RECONCILED — systems agree")
        lines.append("")
        lines.append("No breaks found. Every transaction in the source file "
                     "has an identical match in the ledger, and vice versa.")
    else:
        lines.append(
            f"## Verdict: ⚠️ BREAKS FOUND — "
            f"{summary['break_count']} break(s) worth "
            f"{money(summary['total_break_value'])}")
        lines.append("")
        lines.append("Do not close the day until Finance clears the breaks "
                     "listed below.")
    lines += [
        "",
        "## Totals",
        "",
        f"- **Source rows:** {summary['source_rows']} "
        f"(total {money(summary['source_total'])})",
        f"- **Ledger rows:** {summary['ledger_rows']} "
        f"(total {money(summary['ledger_total'])})",
        f"- **Matched exactly:** {summary['matched']} transactions",
        f"- **Net difference (ledger − source):** "
        f"{money(summary['net_difference'])}",
        f"- **Total value of breaks:** "
        f"{money(summary['total_break_value'])}",
    ]
    if summary["largest_break"]:
        lines.append(
            f"- **Largest single break:** {summary['largest_break'][0]} — "
            f"{money(summary['largest_break'][1])}")
    lines += ["", "## Breaks — send these to Finance", ""]
    if summary["break_count"] == 0:
        lines.append("None — nothing to chase.")
    else:
        for txn_id, s_amt, l_amt, diff in summary["amount_mismatch"]:
            lines.append(
                f"- **Amount mismatch:** {txn_id} — source "
                f"{money(s_amt)}, ledger {money(l_amt)} "
                f"(difference {money(diff)})")
        for txn_id, amt in summary["missing_in_ledger"]:
            lines.append(
                f"- **Missing in ledger:** {txn_id} — "
                f"{money(amt)} in the source file, never posted to the ledger")
        for txn_id, amt in summary["missing_in_source"]:
            lines.append(
                f"- **Missing in source:** {txn_id} — "
                f"{money(amt)} in the ledger with no source record")
    lines += [
        "",
        "Amounts are compared on transaction ID using exact decimal "
        "arithmetic. A transaction that appears in only one system is a "
        "break, not a rounding difference — chase it by ID, not by total.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a daily reconciliation summary from two "
                    "settlement files.")
    parser.add_argument("source", help="source system settlement CSV")
    parser.add_argument("ledger", help="ledger settlement CSV")
    parser.add_argument("--date", default="2026-11-16",
                        help="reconciliation date (default: 2026-11-16)")
    parser.add_argument("--out", help="write the report to this file")
    args = parser.parse_args(argv)

    try:
        source = load_csv(args.source)
        ledger = load_csv(args.ledger)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    summary = reconcile(source, ledger)
    report = render_report(summary, Path(args.source).name,
                           Path(args.ledger).name, args.date)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
    print(report, end="")
    return 1 if summary["break_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
