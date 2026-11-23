#!/usr/bin/env python3
"""Tests for the Day 17 Daily BAU Health-Check Report (bau_report.py).

Run from the project directory:
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bau_report

AS_OF = datetime(2026, 11, 23, 9, 20)
SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def load_sample():
    return bau_report.load_inputs(str(SAMPLE_DIR))


class TestSampleData(unittest.TestCase):
    def test_overall_verdict_is_red(self):
        _, overall = bau_report.build_report(load_sample(), AS_OF)
        self.assertEqual(overall, "CRITICAL")

    def test_exit_code_is_two(self):
        self.assertEqual(bau_report.main(
            ["--input-dir", str(SAMPLE_DIR), "--as-of", "2026-11-23T09:20"]),
            2)

    def test_every_section_is_critical(self):
        data = load_sample()
        self.assertEqual(bau_report.worst_severity(
            bau_report.check_services(data["services.csv"])), "CRITICAL")
        self.assertEqual(bau_report.worst_severity(
            bau_report.check_disks(data["disks.csv"])), "CRITICAL")
        self.assertEqual(bau_report.worst_severity(
            bau_report.check_sla(data["sla.csv"], AS_OF)), "CRITICAL")
        self.assertEqual(bau_report.worst_severity(
            bau_report.check_files(data["files.csv"])), "CRITICAL")
        self.assertEqual(bau_report.worst_severity(
            bau_report.check_certs(data["certs.csv"], AS_OF)), "CRITICAL")

    def test_top_action_is_the_down_service(self):
        report, _ = bau_report.build_report(load_sample(), AS_OF)
        first_action = [line for line in report.splitlines()
                        if line.startswith("1. ")][0]
        self.assertIn("notification-service", first_action)
        self.assertIn("DOWN", first_action)

    def test_report_names_the_key_facts(self):
        report, _ = bau_report.build_report(load_sample(), AS_OF)
        for fact in ("settlement-20261123.csv", "INC-2011", "/data",
                     "Payment Gateway API", "1180 ms", "35m over"):
            self.assertIn(fact, report)


class TestSlaMath(unittest.TestCase):
    def test_p1_breached_35_minutes_over(self):
        items = bau_report.check_sla(load_sample()["sla.csv"], AS_OF)
        inc = next(i for i in items if i["ticket"] == "INC-2011")
        self.assertEqual(inc["severity"], "CRITICAL")
        self.assertIn("35m over", inc["detail"])

    def test_p2_at_risk_with_30_minutes_left(self):
        items = bau_report.check_sla(load_sample()["sla.csv"], AS_OF)
        inc = next(i for i in items if i["ticket"] == "INC-2014")
        self.assertEqual(inc["severity"], "WARNING")
        self.assertIn("30m", inc["detail"])

    def test_resolved_ticket_is_excluded(self):
        items = bau_report.check_sla(load_sample()["sla.csv"], AS_OF)
        self.assertNotIn("INC-2010", [i["ticket"] for i in items])
        self.assertEqual(len(items), 5)

    def test_unknown_priority_is_flagged_not_crashed(self):
        rows = [{"ticket": "INC-9999", "priority": "P9", "summary": "Odd one",
                 "opened": "2026-11-23 08:00", "status": "open", "owner": "x"}]
        items = bau_report.check_sla(rows, AS_OF)
        self.assertEqual(items[0]["severity"], "WARNING")
        self.assertIn("unknown priority", items[0]["detail"])


class TestOtherSections(unittest.TestCase):
    def test_disk_hours_to_full(self):
        items = bau_report.check_disks(load_sample()["disks.csv"])
        data_disk = next(i for i in items if i["mount"] == "/data")
        self.assertAlmostEqual(data_disk["hours_to_full"], 6.4, places=1)
        self.assertEqual(data_disk["severity"], "CRITICAL")

    def test_gateway_cert_expires_today(self):
        items = bau_report.check_certs(load_sample()["certs.csv"], AS_OF)
        gateway = next(i for i in items
                       if i["service"] == "Payment Gateway API")
        self.assertEqual(gateway["days"], 0)
        self.assertEqual(gateway["severity"], "CRITICAL")

    def test_degraded_service_is_warning_not_critical(self):
        items = bau_report.check_services(load_sample()["services.csv"])
        settlement = next(i for i in items
                          if i["service"] == "settlement-service")
        self.assertEqual(settlement["severity"], "WARNING")
        self.assertEqual(settlement["latency"], 1180)


class TestVerdictLevels(unittest.TestCase):
    def _write_inputs(self, tmpdir, services, disks, sla, files, certs):
        files_map = {
            "services.csv": services, "disks.csv": disks, "sla.csv": sla,
            "files.csv": files, "certs.csv": certs,
        }
        for name, text in files_map.items():
            Path(tmpdir, name).write_text(text)
        return tmpdir

    def test_all_healthy_is_green_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_inputs(
                tmp,
                "service,status,url,latency_ms,latency_threshold_ms,uptime_pct,"
                "uptime_sla_pct,failed_probes,last_error,down_since\n"
                "payment-api,UP,https://x,100,500,99.99,99.9,0,,\n",
                "mount,total_gb,used_pct,inodes_pct,growth_pct_per_hour\n"
                "/,100,50,40,0.1\n",
                "ticket,priority,summary,opened,status,owner\n"
                "INC-1,P3,Minor,2026-11-23 08:00,open,team\n",
                "filename,expected_by,arrived_at,status,size_bytes,"
                "expected_min_bytes,sender\n"
                "a.csv,2026-11-23 07:00,2026-11-23 06:50,OK,5000,1000,team\n",
                "hostname,service,expiry_date,owner\n"
                "a.example.com,Web,2027-06-01,team\n")
            report, overall = bau_report.build_report(
                bau_report.load_inputs(tmp), AS_OF)
            self.assertEqual(overall, "OK")
            self.assertIn("GREEN", report)
            self.assertEqual(
                bau_report.main(["--input-dir", tmp,
                                 "--as-of", "2026-11-23T09:20"]), 0)

    def test_warnings_only_is_amber_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_inputs(
                tmp,
                "service,status,url,latency_ms,latency_threshold_ms,uptime_pct,"
                "uptime_sla_pct,failed_probes,last_error,down_since\n"
                "payment-api,UP,https://x,100,500,99.99,99.9,0,,\n",
                "mount,total_gb,used_pct,inodes_pct,growth_pct_per_hour\n"
                "/var,600,84,71,0.8\n",
                "ticket,priority,summary,opened,status,owner\n"
                "INC-1,P3,Minor,2026-11-23 08:00,open,team\n",
                "filename,expected_by,arrived_at,status,size_bytes,"
                "expected_min_bytes,sender\n"
                "a.csv,2026-11-23 07:00,2026-11-23 06:50,OK,5000,1000,team\n",
                "hostname,service,expiry_date,owner\n"
                "a.example.com,Web,2026-12-12,team\n")
            report, overall = bau_report.build_report(
                bau_report.load_inputs(tmp), AS_OF)
            self.assertEqual(overall, "WARNING")
            self.assertIn("AMBER", report)
            self.assertEqual(
                bau_report.main(["--input-dir", tmp,
                                 "--as-of", "2026-11-23T09:20"]), 1)

    def test_missing_input_file_is_an_error_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Only one of the five files present.
            Path(tmp, "services.csv").write_text("service,status\nx,UP\n")
            self.assertEqual(
                bau_report.main(["--input-dir", tmp,
                                 "--as-of", "2026-11-23T09:20"]), 2)


if __name__ == "__main__":
    unittest.main()
