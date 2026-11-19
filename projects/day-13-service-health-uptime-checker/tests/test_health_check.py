#!/usr/bin/env python3
"""Tests for Day 13 — Service Health / Uptime Checker."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import health_check as hc

HERE = Path(__file__).resolve().parent.parent
SAMPLE = HERE / "sample_data"


def make_service(**overrides):
    svc = {"name": "svc", "url": "https://internal.example.local/svc/health",
           "expected_status": 200, "max_latency_ms": 500,
           "uptime_sla_percent": 99.5, "critical": True}
    svc.update(overrides)
    return svc


def make_probes(ok=10, fail_tail=0, latency=150, start="2026-11-19 08:00",
                error="Connection refused"):
    """`ok` good probes followed by `fail_tail` failed probes, 5 min apart."""
    base = datetime.strptime(start, hc.TS_FORMAT)
    probes = []
    for i in range(ok):
        probes.append({"timestamp": base + timedelta(minutes=5 * i),
                       "status": 200, "latency_ms": latency, "error": ""})
    for j in range(fail_tail):
        probes.append({"timestamp": base + timedelta(minutes=5 * (ok + j)),
                       "status": 0, "latency_ms": None, "error": error})
    return probes


class TestSampleData(unittest.TestCase):
    def setUp(self):
        self.services = hc.load_services(SAMPLE / "services.json")
        self.probes = hc.load_probes(
            SAMPLE / "probes.csv", [s["name"] for s in self.services])
        self.results, self.verdict, self.reason = hc.check_all(
            self.services, self.probes)
        self.by_name = {r["name"]: r for r in self.results}

    def test_sample_verdict_is_critical(self):
        self.assertEqual(self.verdict, "CRITICAL")
        self.assertEqual(self.reason, "a critical service is DOWN")

    def test_crm_sync_is_down_since_0855(self):
        crm = self.by_name["crm-sync"]
        self.assertEqual(crm["status"], "DOWN")
        self.assertEqual(crm["consecutive_failures"], 6)
        self.assertEqual(crm["outage_since"],
                         datetime(2026, 11, 19, 8, 55))
        self.assertEqual(crm["outage_minutes"], 25)
        self.assertEqual(crm["last_error"], "Connection refused")
        self.assertEqual(crm["uptime_percent"], 97.92)
        self.assertEqual(crm["failures"], 6)
        self.assertEqual(crm["total"], 288)

    def test_settlement_service_is_degraded_on_latency(self):
        stl = self.by_name["settlement-service"]
        self.assertEqual(stl["status"], "DEGRADED")
        self.assertEqual(stl["uptime_percent"], 100.00)
        self.assertEqual(stl["failures"], 0)
        self.assertGreater(stl["avg_latency_ms"], 800)
        self.assertTrue(any("latency" in r for r in stl["reasons"]))

    def test_healthy_services_are_up(self):
        for name in ("payment-api", "customer-portal",
                     "file-gateway", "notification-service"):
            with self.subTest(service=name):
                self.assertEqual(self.by_name[name]["status"], "UP")

    def test_payment_api_survives_one_blip(self):
        api = self.by_name["payment-api"]
        self.assertEqual(api["failures"], 1)
        self.assertEqual(api["uptime_percent"], 99.65)
        self.assertEqual(api["consecutive_failures"], 0)

    def test_report_names_the_down_service_and_outage(self):
        report = hc.render_report(self.results, self.verdict, self.reason,
                                  self.services, 24,
                                  datetime(2026, 11, 19, 9, 20))
        self.assertIn("🔴 CRITICAL", report)
        self.assertIn("crm-sync", report)
        self.assertIn("08:55", report)
        self.assertIn("25 minutes ago", report)
        self.assertIn("settlement-service", report)
        self.assertIn("1279 ms", report)


class TestClassification(unittest.TestCase):
    def test_all_ok_is_up(self):
        result = hc.analyse_service(make_service(),
                                    make_probes(ok=12, latency=150))
        self.assertEqual(result["status"], "UP")
        self.assertEqual(result["uptime_percent"], 100.00)

    def test_two_consecutive_failures_is_down(self):
        result = hc.analyse_service(make_service(),
                                    make_probes(ok=10, fail_tail=2))
        self.assertEqual(result["status"], "DOWN")
        self.assertEqual(result["consecutive_failures"], 2)
        self.assertEqual(result["outage_minutes"], 5)

    def test_one_failure_then_recovery_is_not_down(self):
        # 199 good + 1 failed + 1 recovered = 200/201 = 99.50% uptime,
        # exactly at SLA, and the last probe is good — so UP, not DOWN.
        probes = make_probes(ok=199, fail_tail=1) + [{
            "timestamp": datetime(2026, 11, 19, 8, 30),
            "status": 200, "latency_ms": 150, "error": ""}]
        result = hc.analyse_service(make_service(), probes)
        self.assertEqual(result["status"], "UP")
        self.assertEqual(result["consecutive_failures"], 0)

    def test_uptime_below_sla_is_degraded(self):
        # 1 failure in 12 probes = 91.67% uptime, below the 99.5% SLA.
        probes = make_probes(ok=11, fail_tail=1)
        result = hc.analyse_service(make_service(), probes)
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["uptime_percent"], 91.67)

    def test_slow_but_up_is_degraded(self):
        result = hc.analyse_service(make_service(),
                                    make_probes(ok=12, latency=900))
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["avg_latency_ms"], 900)

    def test_no_probes_is_unknown(self):
        result = hc.analyse_service(make_service(), [])
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["uptime_percent"])
        self.assertEqual(result["reasons"], ["no probes in the window"])

    def test_non_200_status_counts_as_failure(self):
        probes = make_probes(ok=12)
        probes[-1] = {"timestamp": probes[-1]["timestamp"], "status": 503,
                      "latency_ms": 120, "error": ""}
        probes[-2] = {"timestamp": probes[-2]["timestamp"], "status": 503,
                      "latency_ms": 120, "error": ""}
        result = hc.analyse_service(make_service(), probes)
        self.assertEqual(result["status"], "DOWN")
        self.assertEqual(result["failures"], 2)


class TestVerdictAndErrors(unittest.TestCase):
    def test_all_healthy_verdict(self):
        svc = make_service()
        results, verdict, _ = hc.check_all(
            [svc], {"svc": make_probes(ok=12)})
        self.assertEqual(verdict, "ALL HEALTHY")
        self.assertEqual(results[0]["status"], "UP")

    def test_non_critical_down_is_degraded_not_critical(self):
        svc = make_service(critical=False)
        _, verdict, _ = hc.check_all(
            [svc], {"svc": make_probes(ok=10, fail_tail=3)})
        self.assertEqual(verdict, "DEGRADED")

    def test_unknown_service_makes_verdict_degraded(self):
        svc = make_service()
        _, verdict, _ = hc.check_all([svc], {"svc": []})
        self.assertEqual(verdict, "DEGRADED")

    def test_missing_services_file_raises(self):
        with self.assertRaises(hc.HealthCheckError):
            hc.load_services(Path("/tmp/does-not-exist-services.json"))

    def test_probe_for_unknown_service_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                        delete=False) as fh:
            fh.write("timestamp,service,http_status,latency_ms,error\n")
            fh.write("2026-11-19 09:00,mystery-service,200,120,\n")
            path = fh.name
        with self.assertRaises(hc.HealthCheckError):
            hc.load_probes(path, ["svc"])

    def test_bad_timestamp_raises(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv",
                                        delete=False) as fh:
            fh.write("timestamp,service,http_status,latency_ms,error\n")
            fh.write("19/11/2026 09:00,svc,200,120,\n")
            path = fh.name
        with self.assertRaises(hc.HealthCheckError):
            hc.load_probes(path, ["svc"])

    def test_percentile(self):
        self.assertEqual(hc.percentile([100, 200, 300, 400], 95), 400)
        self.assertEqual(hc.percentile([100, 200, 300, 400], 50), 200)
        self.assertEqual(hc.percentile([150], 95), 150)

    def test_main_exit_codes(self):
        healthy = hc.main([str(SAMPLE / "services.json"),
                           str(SAMPLE / "probes.csv")])
        self.assertEqual(healthy, 1)  # sample data is CRITICAL
        missing = hc.main([str(SAMPLE / "services.json"),
                           "/tmp/no-such-probes.csv"])
        self.assertEqual(missing, 2)


if __name__ == "__main__":
    unittest.main()
