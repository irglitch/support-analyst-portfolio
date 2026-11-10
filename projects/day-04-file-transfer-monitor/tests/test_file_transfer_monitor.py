import sys
import unittest
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from file_transfer_monitor import (
    build_report,
    check_transfers,
    load_manifest,
    load_transfer_log,
    overall_status,
    parse_hhmm,
)

BASE = Path(__file__).resolve().parents[1]
SAMPLE = BASE / "sample_data"


class TestFileTransferMonitor(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest(SAMPLE / "expected_files.csv")
        self.received = load_transfer_log(SAMPLE / "transfer_log_20261110.csv")
        self.now = parse_hhmm("07:30")
        self.results, self.unexpected = check_transfers(
            self.manifest, self.received, self.now,
            drop_dir=SAMPLE / "incoming",
        )
        self.by_name = {r["filename"]: r for r in self.results}

    def test_missing_settlement_file_detected(self):
        self.assertEqual(self.by_name["settlement_20261110.csv"]["status"], "MISSING")

    def test_zero_byte_file_flagged_empty(self):
        self.assertEqual(self.by_name["audit_log_20261110.csv"]["status"], "EMPTY")

    def test_late_file_flagged(self):
        rates = self.by_name["rates_20261110.csv"]
        self.assertEqual(rates["status"], "LATE")
        self.assertIn("06:47", rates["note"])

    def test_on_time_file_ok(self):
        self.assertEqual(self.by_name["customer_feed_20261110.csv"]["status"], "OK")

    def test_unexpected_file_flagged(self):
        self.assertIn("promo_codes_20261110.csv", self.unexpected)

    def test_missing_critical_file_is_alert_exit_2(self):
        label, code, detail = overall_status(self.results)
        self.assertEqual(code, 2)
        self.assertIn("ALERT", label)
        self.assertIn("settlement_20261110.csv", detail)

    def test_small_file_flagged(self):
        # Synthetic: a file that arrived on time but below its minimum size
        manifest = [{
            "filename": "tiny.csv", "expected_by": time(7, 0),
            "expected_by_raw": "07:00", "source": "Test", "min_size_bytes": 500,
            "critical": False, "business_impact": "test",
        }]
        received = {"tiny.csv": {
            "received_at": time(6, 0), "received_at_raw": "06:00",
            "size_bytes": 42,
        }}
        results, _ = check_transfers(manifest, received, self.now)
        self.assertEqual(results[0]["status"], "SMALL")

    def test_report_names_the_missing_file(self):
        report = build_report(self.results, self.unexpected, "07:30",
                              "expected_files.csv")
        self.assertIn("settlement_20261110.csv", report)
        self.assertIn("MISSING", report)
        self.assertIn("File Transfer Status Report", report)

    def test_all_ok_gives_exit_0(self):
        manifest = [{
            "filename": "a.csv", "expected_by": time(7, 0),
            "expected_by_raw": "07:00", "source": "Test", "min_size_bytes": 10,
            "critical": False, "business_impact": "test",
        }]
        received = {"a.csv": {
            "received_at": time(6, 30), "received_at_raw": "06:30",
            "size_bytes": 100,
        }}
        results, _ = check_transfers(manifest, received, self.now)
        label, code, _ = overall_status(results)
        self.assertEqual(code, 0)
        self.assertIn("OK", label)


if __name__ == "__main__":
    unittest.main()
