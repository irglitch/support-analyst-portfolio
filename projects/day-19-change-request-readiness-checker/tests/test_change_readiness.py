#!/usr/bin/env python3
"""Tests for the Day 19 Change Request Readiness Checker (Python stdlib unittest)."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import change_readiness

BASE = {
    "change_id": "CHG-9999",
    "title": "Test change",
    "service": "test-api",
    "risk": "medium",
    "change_type": "normal",
    "implementer": "test-team",
    "scheduled_start": "2026-11-26T22:00",
    "scheduled_end": "2026-11-26T23:00",
    "estimated_duration_minutes": 20,
    "description": "A sufficiently long test description for CAB.",
    "touches_limits": False,
    "impact": {"services": ["test-api"], "outage_expected": False},
    "test_evidence": {"environment": "staging", "result": "pass", "load_tested": False},
    "rollback": {"plan": "Restore the previous build", "trigger": "Error rate above 5%",
                 "estimated_minutes": 10},
    "approvals": [{"approver": "service-owner", "role": "service owner", "status": "approved"}],
    "cab_approved": False,
    "communications": {"stakeholders_notified": True},
    "dependencies_checked": True,
    "peer_reviewed": True,
    "verification_steps": ["Check the health endpoint"],
}


def fresh(**overrides):
    change = copy.deepcopy(BASE)
    change.update(overrides)
    return change


class TestVerdicts(unittest.TestCase):
    def test_complete_change_is_ready(self):
        blockers, warnings, _ = change_readiness.check_change(fresh())
        self.assertEqual(blockers, [])
        self.assertEqual(warnings, [])
        self.assertEqual(change_readiness.verdict(blockers, warnings), "READY")

    def test_placeholder_rollback_trigger_blocks(self):
        change = fresh()
        change["rollback"]["trigger"] = "TBD"
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("rollback trigger" in b for b in blockers))

    def test_pending_approval_blocks(self):
        change = fresh()
        change["approvals"][0]["status"] = "pending"
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("Approval still outstanding" in b for b in blockers))

    def test_window_too_short_to_roll_back_blocks(self):
        # 50m implementation + 20m rollback cannot fit a 60m window.
        change = fresh(estimated_duration_minutes=50)
        change["rollback"]["estimated_minutes"] = 20
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("Window too short to roll back" in b for b in blockers))

    def test_tight_window_warns_but_does_not_block(self):
        # 40m + 10m = 50m of a 60m window: fits, but over the 80% line.
        change = fresh(estimated_duration_minutes=40)
        blockers, warnings, _ = change_readiness.check_change(change)
        self.assertEqual(blockers, [])
        self.assertTrue(any("tight" in w for w in warnings))
        self.assertEqual(change_readiness.verdict(blockers, warnings), "READY WITH CONDITIONS")

    def test_high_risk_without_load_test_blocks(self):
        change = fresh(risk="high", cab_approved=True)
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("load-test" in b for b in blockers))

    def test_limit_change_without_load_test_blocks(self):
        change = fresh(touches_limits=True)
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("load-test" in b for b in blockers))

    def test_high_risk_with_load_test_and_cab_passes(self):
        change = fresh(risk="high", cab_approved=True)
        change["test_evidence"]["load_tested"] = True
        blockers, warnings, _ = change_readiness.check_change(change)
        self.assertEqual(blockers, [])
        self.assertEqual(warnings, [])

    def test_high_risk_without_cab_approval_blocks(self):
        change = fresh(risk="high")
        change["test_evidence"]["load_tested"] = True
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("CAB approval" in b for b in blockers))

    def test_implementer_as_only_approver_blocks(self):
        change = fresh()
        change["approvals"] = [{"approver": "test-team", "role": "service owner", "status": "approved"}]
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("separation of duties" in b for b in blockers))

    def test_outage_without_notice_blocks_quiet_change_warns(self):
        change = fresh()
        change["communications"]["stakeholders_notified"] = False
        change["impact"]["outage_expected"] = True
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("Outage expected" in b for b in blockers))

        quiet = fresh()
        quiet["communications"]["stakeholders_notified"] = False
        blockers, warnings, _ = change_readiness.check_change(quiet)
        self.assertEqual(blockers, [])
        self.assertTrue(any("not yet notified" in w for w in warnings))

    def test_failed_test_evidence_blocks(self):
        change = fresh()
        change["test_evidence"]["result"] = "fail"
        blockers, _, _ = change_readiness.check_change(change)
        self.assertTrue(any("test evidence" in b for b in blockers))

    def test_missing_verification_steps_block(self):
        blockers, _, _ = change_readiness.check_change(fresh(verification_steps=[]))
        self.assertTrue(any("verification" in b for b in blockers))


class TestCli(unittest.TestCase):
    def write_input(self, changes, tmp):
        path = Path(tmp) / "changes.json"
        path.write_text(json.dumps({"review_for": "Test CAB", "changes": changes}))
        return path

    def test_cli_ready_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh()], tmp)
            out = Path(tmp) / "report.md"
            rc = change_readiness.main([str(path), "--out", str(out), "--generated-at", "2026-11-25 09:20"])
            self.assertEqual(rc, 0)
            self.assertIn("READY — every change passes", out.read_text())

    def test_cli_blocked_exit_one(self):
        change = fresh()
        change["rollback"]["trigger"] = ""
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([change], tmp)
            out = Path(tmp) / "report.md"
            rc = change_readiness.main([str(path), "--out", str(out)])
            self.assertEqual(rc, 1)
            text = out.read_text()
            self.assertIn("NOT READY", text)
            self.assertIn("CHG-9999", text)

    def test_cli_single_change_filter(self):
        blocked = fresh(change_id="CHG-8888")
        blocked["approvals"] = []
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh(), blocked], tmp)
            out = Path(tmp) / "report.md"
            rc = change_readiness.main([str(path), "--out", str(out), "--change", "CHG-9999"])
            self.assertEqual(rc, 0)  # the blocked change is filtered out

    def test_cli_bad_json_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{ not json")
            self.assertEqual(change_readiness.main([str(path)]), 2)

    def test_cli_missing_file_exit_two(self):
        self.assertEqual(change_readiness.main(["/nonexistent/changes.json"]), 2)

    def test_cli_unknown_change_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_input([fresh()], tmp)
            self.assertEqual(change_readiness.main([str(path), "--change", "CHG-0000"]), 2)


if __name__ == "__main__":
    unittest.main()
