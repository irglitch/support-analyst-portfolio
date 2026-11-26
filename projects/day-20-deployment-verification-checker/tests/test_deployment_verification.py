#!/usr/bin/env python3
"""Tests for the Day 20 Deployment Verification Checker (Python stdlib unittest)."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import deployment_verification

BASE = {
    "deployment_id": "CHG-9999",
    "title": "Test deployment",
    "service": "test-api",
    "expected": {
        "outcome": "deployed",
        "version": "v2.0.0",
        "previous_version": "v1.0.0",
        "instances": 2,
        "smoke_test": "test request end to end",
        "max_error_rate_pct": 2.0,
        "rollback_trigger_pct": 5.0,
        "window_end": "2026-11-25T23:30",
    },
    "observed": {
        "deployment_status": "completed",
        "completed_at": "2026-11-25T22:45",
        "instances": [
            {"name": "test-01", "version": "v2.0.0"},
            {"name": "test-02", "version": "v2.0.0"},
        ],
        "health": "ok",
        "smoke_test_result": "pass",
        "error_rate_pct": 0.3,
    },
}


def fresh(**overrides):
    deployment = copy.deepcopy(BASE)
    deployment.update(overrides)
    return deployment


class TestVerdicts(unittest.TestCase):
    def test_clean_deployment_is_verified(self):
        failures, warnings, _ = deployment_verification.check_deployment(fresh())
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])
        self.assertEqual(deployment_verification.verdict(failures, warnings), "VERIFIED")

    def test_partial_deployment_fails(self):
        deployment = fresh()
        deployment["observed"]["instances"][1]["version"] = "v1.0.0"
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("Partial deployment" in f and "test-02" in f for f in failures))

    def test_missing_instance_fails(self):
        deployment = fresh()
        deployment["observed"]["instances"] = deployment["observed"]["instances"][:1]
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("cannot be verified" in f for f in failures))

    def test_config_mismatch_fails(self):
        deployment = fresh()
        deployment["expected"]["config"] = {"retry_limit": 5}
        deployment["observed"]["instances"][0]["config"] = {"retry_limit": 5}
        deployment["observed"]["instances"][1]["config"] = {"retry_limit": 3}
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("retry_limit" in f and "test-02" in f for f in failures))

    def test_failed_smoke_test_fails(self):
        deployment = fresh()
        deployment["observed"]["smoke_test_result"] = "fail"
        deployment["observed"]["smoke_test_detail"] = "HTTP 500"
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("Smoke test FAILED" in f for f in failures))

    def test_smoke_test_not_run_fails(self):
        deployment = fresh()
        del deployment["observed"]["smoke_test_result"]
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("Smoke test not run" in f for f in failures))

    def test_error_rate_over_rollback_trigger_fails(self):
        deployment = fresh()
        deployment["observed"]["error_rate_pct"] = 6.4
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("rollback trigger" in f for f in failures))

    def test_error_rate_over_warning_level_warns(self):
        deployment = fresh()
        deployment["observed"]["error_rate_pct"] = 3.8
        failures, warnings, _ = deployment_verification.check_deployment(deployment)
        self.assertEqual(failures, [])
        self.assertTrue(any("warning level" in w for w in warnings))
        self.assertEqual(deployment_verification.verdict(failures, warnings),
                         "VERIFIED WITH WARNINGS")

    def test_window_overrun_warns(self):
        deployment = fresh()
        deployment["observed"]["completed_at"] = "2026-11-25T23:41"
        failures, warnings, _ = deployment_verification.check_deployment(deployment)
        self.assertEqual(failures, [])
        self.assertTrue(any("11m after the window" in w for w in warnings))

    def test_old_certificate_still_live_fails(self):
        deployment = fresh()
        deployment["expected"]["cert_expiry_on_or_after"] = "2027-01-01"
        deployment["observed"]["cert_expiry_live"] = "2026-12-10"
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("old certificate" in f for f in failures))

    def test_new_certificate_live_passes(self):
        deployment = fresh()
        deployment["expected"]["cert_expiry_on_or_after"] = "2027-01-01"
        deployment["observed"]["cert_expiry_live"] = "2027-12-01"
        failures, warnings, _ = deployment_verification.check_deployment(deployment)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])

    def test_failed_deployment_fails(self):
        deployment = fresh()
        deployment["observed"]["deployment_status"] = "failed"
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("FAILED" in f for f in failures))

    def test_held_change_not_deployed_is_verified(self):
        deployment = fresh()
        deployment["expected"] = {"outcome": "held", "previous_version": "v1.0.0"}
        deployment["observed"] = {
            "deployment_status": "not_deployed",
            "health": "ok",
            "instances": [{"name": "test-01", "version": "v1.0.0"}],
        }
        failures, warnings, _ = deployment_verification.check_deployment(deployment)
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])

    def test_held_change_deployed_anyway_fails(self):
        deployment = fresh()
        deployment["expected"] = {"outcome": "held", "previous_version": "v1.0.0"}
        failures, _, _ = deployment_verification.check_deployment(deployment)
        self.assertTrue(any("despite the CAB deferral" in f for f in failures))


class TestCli(unittest.TestCase):
    def write_input(self, deployments, tmp):
        path = Path(tmp) / "deployments.json"
        path.write_text(json.dumps({"window": "Test window", "deployments": deployments}))
        return path

    def test_cli_verified_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh()], tmp)
            out = Path(tmp) / "report.md"
            rc = deployment_verification.main([str(path), "--out", str(out),
                                               "--generated-at", "2026-11-26 09:20"])
            self.assertEqual(rc, 0)
            self.assertIn("VERIFIED — every deployment matches", out.read_text())

    def test_cli_failed_exit_one(self):
        deployment = fresh()
        deployment["observed"]["instances"][0]["version"] = "v1.0.0"
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([deployment], tmp)
            out = Path(tmp) / "report.md"
            rc = deployment_verification.main([str(path), "--out", str(out)])
            self.assertEqual(rc, 1)
            text = out.read_text()
            self.assertIn("FAILED", text)
            self.assertIn("CHG-9999", text)

    def test_cli_single_deployment_filter(self):
        failed = fresh(deployment_id="CHG-8888")
        failed["observed"]["deployment_status"] = "failed"
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh(), failed], tmp)
            out = Path(tmp) / "report.md"
            rc = deployment_verification.main([str(path), "--out", str(out),
                                               "--deployment", "CHG-9999"])
            self.assertEqual(rc, 0)  # the failed deployment is filtered out

    def test_cli_bad_json_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{ not json")
            self.assertEqual(deployment_verification.main([str(path)]), 2)

    def test_cli_missing_file_exit_two(self):
        self.assertEqual(deployment_verification.main(["/nonexistent/deployments.json"]), 2)

    def test_cli_unknown_deployment_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh()], tmp)
            self.assertEqual(deployment_verification.main([str(path), "--deployment", "CHG-0000"]), 2)


if __name__ == "__main__":
    unittest.main()
