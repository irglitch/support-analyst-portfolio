"""Tests for Day 10 — Pre-Batch Data Validation Checker."""
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running from the repo root as well as from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validator

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SAMPLE = PROJECT / "sample_data" / "staging_settlements.csv"

HEADER = ("txn_id,customer_id,amount,currency,txn_date,account_no,status\n")
CLEAN = "TXN-9000,CUST-900,10.00,CAD,2026-11-16,ACC-9000,settled\n"


def write_csv(rows):
    """Write rows (list of CSV lines, no header) to a temp file; return path."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                     newline="", encoding="utf-8")
    fh.write(HEADER)
    fh.write("\n".join(rows) + "\n")
    fh.close()
    return fh.name


def run_on_rows(rows):
    path = write_csv(rows)
    try:
        return validator.check(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestSampleData(unittest.TestCase):
    def test_headline_totals(self):
        report, n_blocked = validator.check(str(SAMPLE))
        self.assertIn("**Rows in file:** 20", report)
        self.assertIn("**Valid rows:** 10 (total $1,390.59)", report)
        self.assertIn("**Blocked rows:** 10", report)
        self.assertIn("**Rules failed:** 9 of 9", report)
        self.assertEqual(n_blocked, 10)

    def test_verdict_blocked(self):
        report, _ = validator.check(str(SAMPLE))
        self.assertIn("🔴 BLOCKED", report)

    def test_every_rule_fires(self):
        report, _ = validator.check(str(SAMPLE))
        for label in ("Duplicate transaction ID", "Missing amount",
                      "Negative amount", "Zero amount",
                      "Unexpected currency", "Future transaction date",
                      "Malformed account number", "Missing customer ID",
                      "Invalid status"):
            self.assertIn(label, report)

    def test_bad_rows_named(self):
        report, _ = validator.check(str(SAMPLE))
        for txn_id in ("TXN-4100", "TXN-4103", "TXN-4104", "TXN-4105",
                       "TXN-4106", "TXN-4107", "TXN-4108", "TXN-4109",
                       "TXN-4110"):
            self.assertIn(txn_id, report)


class TestCleanFile(unittest.TestCase):
    def test_clean_row_passes(self):
        report, n_blocked = run_on_rows([CLEAN.strip()])
        self.assertEqual(n_blocked, 0)
        self.assertIn("🟢 GO", report)

    def test_yesterday_date_is_fine(self):
        row = "TXN-9001,CUST-901,10.00,CAD,2026-11-15,ACC-9001,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 0)

    def test_usd_is_allowed(self):
        row = "TXN-9002,CUST-902,10.00,USD,2026-11-16,ACC-9002,pending"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 0)


class TestEachRule(unittest.TestCase):
    def test_duplicate_flags_both_rows(self):
        rows = [CLEAN.strip(),
                "TXN-9000,CUST-900,10.00,CAD,2026-11-16,ACC-9000,settled"]
        _, n_blocked = run_on_rows(rows)
        self.assertEqual(n_blocked, 2)

    def test_missing_amount(self):
        row = "TXN-9003,CUST-903,,CAD,2026-11-16,ACC-9003,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_negative_amount(self):
        row = "TXN-9004,CUST-904,-5.00,CAD,2026-11-16,ACC-9004,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_zero_amount(self):
        row = "TXN-9005,CUST-905,0.00,CAD,2026-11-16,ACC-9005,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_unexpected_currency(self):
        row = "TXN-9006,CUST-906,10.00,EUR,2026-11-16,ACC-9006,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_future_date(self):
        row = "TXN-9007,CUST-907,10.00,CAD,2026-11-17,ACC-9007,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_malformed_account(self):
        row = "TXN-9008,CUST-908,10.00,CAD,2026-11-16,ACC-90X8,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_missing_customer(self):
        row = "TXN-9009,CUST-909,10.00,CAD,2026-11-16,ACC-9009,settled"
        row = row.replace("CUST-909", "")
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_invalid_status(self):
        row = "TXN-9010,CUST-910,10.00,CAD,2026-11-16,ACC-9010,error"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)

    def test_one_bad_row_counts_once(self):
        # Missing amount AND missing customer on the same row: still 1 row.
        row = "TXN-9011,, ,CAD,2026-11-16,ACC-9011,settled"
        _, n_blocked = run_on_rows([row])
        self.assertEqual(n_blocked, 1)


if __name__ == "__main__":
    unittest.main()
