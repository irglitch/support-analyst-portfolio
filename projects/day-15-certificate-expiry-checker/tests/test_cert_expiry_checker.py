import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cert_expiry_checker import (
    build_report,
    classify,
    days_remaining,
    load_inventory,
)

AS_OF = date(2026, 11, 21)


class TestCertExpiryChecker(unittest.TestCase):
    def setUp(self):
        self.sample = (Path(__file__).resolve().parents[1]
                       / "sample_data" / "certificates.csv")
        self.certs = load_inventory(self.sample)

    def test_loads_all_sample_certificates(self):
        self.assertEqual(len(self.certs), 7)
        hostnames = {c["hostname"] for c in self.certs}
        self.assertIn("api.payments.example.com", hostnames)
        self.assertIn("sftp.partnerbank.example.com", hostnames)

    def test_days_remaining_for_expired_cert(self):
        sftp = next(c for c in self.certs
                    if c["hostname"] == "sftp.partnerbank.example.com")
        self.assertEqual(days_remaining(sftp, AS_OF), -2)

    def test_classification_thresholds(self):
        self.assertEqual(classify(-1), "EXPIRED")
        self.assertEqual(classify(0), "CRITICAL")
        self.assertEqual(classify(2), "CRITICAL")
        self.assertEqual(classify(14), "CRITICAL")
        self.assertEqual(classify(15), "WARNING")
        self.assertEqual(classify(24), "WARNING")
        self.assertEqual(classify(30), "WARNING")
        self.assertEqual(classify(31), "OK")
        self.assertEqual(classify(101), "OK")

    def test_sample_counts(self):
        report, worst = build_report(self.certs, AS_OF)
        self.assertEqual(worst, "EXPIRED")
        self.assertIn("🔴 EXPIRED: **1**", report)
        self.assertIn("🔴 CRITICAL (≤ 14 days): **1**", report)
        self.assertIn("🟡 WARNING (≤ 30 days): **2**", report)
        self.assertIn("🟢 OK: **3**", report)

    def test_report_flags_the_expired_and_critical_hosts(self):
        report, _ = build_report(self.certs, AS_OF)
        self.assertIn("sftp.partnerbank.example.com", report)
        self.assertIn("api.payments.example.com", report)
        self.assertIn("Needs action", report)

    def test_all_ok_inventory_reports_ok(self):
        healthy = [c for c in self.certs
                   if days_remaining(c, AS_OF) > 30]
        report, worst = build_report(healthy, AS_OF)
        self.assertEqual(worst, "OK")
        self.assertIn("**Overall: 🟢 OK**", report)


if __name__ == "__main__":
    unittest.main()
