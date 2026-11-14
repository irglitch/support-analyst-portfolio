"""Tests for Day 08 — Duplicate Transaction Detector."""
import csv
import io
import tempfile
import unittest
from pathlib import Path

import duplicate_detector

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SAMPLE = PROJECT / "sample_data" / "transactions.csv"

HEADER = "txn_id,customer_id,txn_timestamp,amount,status\n"


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
        return duplicate_detector.detect(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestSampleData(unittest.TestCase):
    def test_headline_totals(self):
        report, n_dupes = duplicate_detector.detect(str(SAMPLE))
        self.assertIn("**Transactions in extract:** 22", report)
        self.assertIn("**Unique transaction IDs:** 20", report)
        self.assertIn("**Total value posted:** $2,845.50", report)

    def test_exact_duplicates_found(self):
        report, n_dupes = duplicate_detector.detect(str(SAMPLE))
        self.assertIn("TXN-3001", report)
        self.assertIn("TXN-3005", report)
        self.assertIn("**Duplicate extra charges:** 3", report)
        self.assertIn("**Amount at risk:** $208.73", report)
        self.assertEqual(n_dupes, 3)

    def test_near_duplicate_pair_found(self):
        report, _ = duplicate_detector.detect(str(SAMPLE))
        # Double-click pair: TXN-3004 then TXN-3010, 147 seconds apart.
        self.assertIn("TXN-3004", report)
        self.assertIn("TXN-3010", report)
        self.assertIn("147", report)

    def test_legitimate_repeats_not_flagged(self):
        report, _ = duplicate_detector.detect(str(SAMPLE))
        # TXN-3014 is a legit repeat (5 hours later); TXN-3017 is a
        # different customer. Neither may appear in the duplicate tables.
        exact_section = report.split("## 2.")[0]
        near_section = report.split("## 2.")[1].split("## How")[0]
        self.assertNotIn("TXN-3014", exact_section)
        self.assertNotIn("TXN-3014", near_section)
        self.assertNotIn("TXN-3017", near_section)


class TestCleanData(unittest.TestCase):
    def test_no_duplicates_is_clean(self):
        rows = [
            "TXN-9001,CUST-201,2026-11-13 08:00:00,10.00,completed",
            "TXN-9002,CUST-202,2026-11-13 08:05:00,20.00,completed",
            "TXN-9003,CUST-201,2026-11-13 18:00:00,10.00,completed",
        ]
        report, n_dupes = run_on_rows(rows)
        self.assertEqual(n_dupes, 0)
        self.assertIn("✅ CLEAN", report)
        self.assertIn("**Total value posted:** $40.00", report)

    def test_same_customer_same_amount_hours_apart_is_clean(self):
        rows = [
            "TXN-9001,CUST-201,2026-11-13 08:00:00,10.00,completed",
            "TXN-9002,CUST-201,2026-11-13 20:00:00,10.00,completed",
        ]
        _, n_dupes = run_on_rows(rows)
        self.assertEqual(n_dupes, 0)

    def test_exact_duplicate_counts_extra_charge_once(self):
        rows = [
            "TXN-9001,CUST-201,2026-11-13 08:00:00,10.00,completed",
            "TXN-9001,CUST-201,2026-11-13 08:00:00,10.00,completed",
            "TXN-9001,CUST-201,2026-11-13 08:00:00,10.00,completed",
            "TXN-9002,CUST-202,2026-11-13 08:05:00,20.00,completed",
        ]
        report, n_dupes = run_on_rows(rows)
        self.assertEqual(n_dupes, 2)  # posted 3x = 2 extra charges
        self.assertIn("**Amount at risk:** $20.00", report)

    def test_bad_amount_raises(self):
        rows = ["TXN-9001,CUST-201,2026-11-13 08:00:00,not-a-number,completed"]
        with self.assertRaises(ValueError):
            run_on_rows(rows)


if __name__ == "__main__":
    unittest.main()
