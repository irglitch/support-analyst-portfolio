#!/usr/bin/env python3
"""Tests for Day 11 — Reconciliation Summary Report Generator."""
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reconcile_report import load_csv, reconcile, render_report, main  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SAMPLE_SOURCE = PROJECT / "sample_data" / "source_settlements.csv"
SAMPLE_LEDGER = PROJECT / "sample_data" / "ledger_settlements.csv"


def _write_csv(path, rows):
    header = "txn_id,customer_id,amount,currency,txn_date,account_no,status\n"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(header)
        for row in rows:
            fh.write(",".join(row) + "\n")


class TestLoadCsv(unittest.TestCase):
    def test_loads_sample_files(self):
        source = load_csv(SAMPLE_SOURCE)
        ledger = load_csv(SAMPLE_LEDGER)
        self.assertEqual(len(source), 18)
        self.assertEqual(len(ledger), 18)
        self.assertEqual(source["TXN-5200"]["amount"], Decimal("45.00"))

    def test_missing_file_is_value_error(self):
        with self.assertRaises(ValueError):
            load_csv(PROJECT / "sample_data" / "no_such_file.csv")

    def test_duplicate_txn_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.csv"
            _write_csv(path, [
                ["TXN-1", "C1", "10.00", "CAD", "2026-11-16", "ACC-1001", "settled"],
                ["TXN-1", "C1", "10.00", "CAD", "2026-11-16", "ACC-1001", "settled"],
            ])
            with self.assertRaises(ValueError):
                load_csv(path)

    def test_bad_amount_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            _write_csv(path, [
                ["TXN-1", "C1", "ten", "CAD", "2026-11-16", "ACC-1001", "settled"],
            ])
            with self.assertRaises(ValueError):
                load_csv(path)


class TestReconcile(unittest.TestCase):
    def test_sample_data_summary(self):
        summary = reconcile(load_csv(SAMPLE_SOURCE), load_csv(SAMPLE_LEDGER))
        self.assertEqual(summary["matched"], 16)
        self.assertEqual(summary["break_count"], 3)
        self.assertEqual(len(summary["amount_mismatch"]), 1)
        self.assertEqual(len(summary["missing_in_ledger"]), 1)
        self.assertEqual(len(summary["missing_in_source"]), 1)
        self.assertEqual(summary["source_total"], Decimal("2550.19"))
        self.assertEqual(summary["ledger_total"], Decimal("2575.20"))
        self.assertEqual(summary["net_difference"], Decimal("25.01"))
        self.assertEqual(summary["total_break_value"], Decimal("214.99"))
        self.assertEqual(summary["largest_break"][0], "Missing in source TXN-5210")
        self.assertEqual(summary["largest_break"][1], Decimal("120.00"))

    def test_amount_mismatch_details(self):
        summary = reconcile(load_csv(SAMPLE_SOURCE), load_csv(SAMPLE_LEDGER))
        txn_id, s_amt, l_amt, diff = summary["amount_mismatch"][0]
        self.assertEqual(txn_id, "TXN-5203")
        self.assertEqual((s_amt, l_amt, diff),
                         (Decimal("250.00"), Decimal("245.00"), Decimal("-5.00")))

    def test_identical_files_reconcile_clean(self):
        rows = load_csv(SAMPLE_SOURCE)
        summary = reconcile(rows, dict(rows))
        self.assertEqual(summary["break_count"], 0)
        self.assertEqual(summary["matched"], 18)
        self.assertEqual(summary["net_difference"], Decimal("0"))
        self.assertIsNone(summary["largest_break"])

    def test_empty_files_reconcile_clean(self):
        summary = reconcile({}, {})
        self.assertEqual(summary["break_count"], 0)
        self.assertEqual(summary["source_total"], Decimal("0"))


class TestReportAndCli(unittest.TestCase):
    def test_report_names_each_break(self):
        summary = reconcile(load_csv(SAMPLE_SOURCE), load_csv(SAMPLE_LEDGER))
        report = render_report(summary, "source_settlements.csv",
                               "ledger_settlements.csv", "2026-11-16")
        for txn_id in ("TXN-5203", "TXN-5207", "TXN-5210"):
            self.assertIn(txn_id, report)
        self.assertIn("BREAKS FOUND", report)
        self.assertIn("$2,550.19", report)
        self.assertIn("$2,575.20", report)
        self.assertIn("$214.99", report)

    def test_clean_report_says_reconciled(self):
        rows = load_csv(SAMPLE_SOURCE)
        summary = reconcile(rows, dict(rows))
        report = render_report(summary, "a.csv", "b.csv", "2026-11-16")
        self.assertIn("RECONCILED", report)
        self.assertIn("None — nothing to chase.", report)

    def test_cli_exit_code_and_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "summary.md"
            rc = main([str(SAMPLE_SOURCE), str(SAMPLE_LEDGER),
                       "--out", str(out)])
            self.assertEqual(rc, 1)  # breaks found
            self.assertTrue(out.exists())
            self.assertIn("TXN-5210", out.read_text(encoding="utf-8"))

    def test_cli_clean_files_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "summary.md"
            rc = main([str(SAMPLE_SOURCE), str(SAMPLE_SOURCE),
                       "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertIn("RECONCILED", out.read_text(encoding="utf-8"))

    def test_cli_missing_file_exit_two(self):
        rc = main([str(SAMPLE_SOURCE), str(PROJECT / "missing.csv")])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
