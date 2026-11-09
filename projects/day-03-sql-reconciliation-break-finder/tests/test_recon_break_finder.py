import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recon_break_finder import money, reconcile, run_queries, to_cents
import sqlite3


class TestReconBreakFinder(unittest.TestCase):
    def setUp(self):
        self.base = Path(__file__).resolve().parents[1]
        self.billing = self.base / "sample_data" / "billing_extract.csv"
        self.ledger = self.base / "sample_data" / "finance_ledger.csv"
        self.report = reconcile(str(self.billing), str(self.ledger))

    def test_totals_differ_by_64_23(self):
        self.assertIn("$3,540.23", self.report)  # billing total
        self.assertIn("$3,476.00", self.report)  # ledger total
        self.assertIn("$64.23", self.report)     # difference

    def test_missing_in_ledger_found(self):
        # TXN-2007 was billed for $145.00 but never posted.
        self.assertIn("TXN-2007", self.report)
        self.assertIn("$145.00", self.report)

    def test_orphan_in_ledger_found(self):
        # TXN-2017 was posted for $89.50 with no matching bill.
        self.assertIn("TXN-2017", self.report)
        self.assertIn("$89.50", self.report)

    def test_amount_mismatches_found(self):
        # TXN-2003: billed $210.00, posted $201.00 (transposed digits).
        # TXN-2012: billed $75.25, posted $75.52.
        self.assertIn("TXN-2003", self.report)
        self.assertIn("TXN-2012", self.report)
        self.assertIn("$201.00", self.report)
        self.assertIn("$75.52", self.report)

    def test_matched_majority_agrees(self):
        # 13 of 16 billing transactions match the ledger exactly.
        self.assertIn("13", self.report)
        self.assertIn("BREAK FOUND", self.report)

    def test_money_formatting(self):
        self.assertEqual(money(354023), "$3,540.23")
        self.assertEqual(money(-900), "-$9.00")
        self.assertEqual(money(0), "$0.00")
        self.assertEqual(to_cents("210.00"), 21000)


if __name__ == "__main__":
    unittest.main()
