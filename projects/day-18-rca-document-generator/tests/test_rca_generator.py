#!/usr/bin/env python3
"""Tests for the Day 18 RCA Document Generator (Python stdlib unittest)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rca_generator

BASE = {
    "incident_id": "INC-9999",
    "title": "Test outage",
    "priority": "P1",
    "service": "test-api",
    "detected_at": "2026-11-24T09:00",
    "resolved_at": "2026-11-24T10:30",
    "summary": "Test summary.",
    "root_cause": "Test root cause.",
    "business_impact": "$1,000 affected.",
    "impact": {
        "users_affected": "100",
        "failed_transactions": "50",
        "detection": "Probe alert",
    },
    "timeline": [
        {"time": "2026-11-24T09:00", "event": "Detected"},
        {"time": "2026-11-24T09:45", "event": "Fix applied"},
        {"time": "2026-11-24T10:30", "event": "Resolved"},
    ],
    "five_whys": ["Why 1.", "Why 2.", "Why 3.", "Why 4.", "Why 5."],
    "went_well": ["Detection was fast."],
    "went_badly": ["No runbook existed."],
    "action_items": [
        {"action": "Write the runbook", "owner": "Support", "due": "2026-11-28", "status": "Open"}
    ],
    "evidence": ["Probe log 09:00–10:30."],
    "follow_up": "Review next week.",
    "author": "Tester",
    "timezone": "America/Toronto",
}


def write_incident(data, tmp):
    path = Path(tmp) / "incident.json"
    path.write_text(json.dumps(data))
    return path


class TestCompleteness(unittest.TestCase):
    def test_complete_p1_is_final(self):
        text, missing = rca_generator.render(dict(BASE), rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertEqual(missing, [])
        self.assertIn("**Status:** FINAL", text)
        self.assertIn("Test root cause.", text)
        self.assertIn("1h 30m", text)  # 09:00 -> 10:30 duration

    def test_missing_root_cause_is_draft(self):
        incident = dict(BASE)
        incident.pop("root_cause")
        text, missing = rca_generator.render(incident, rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertTrue(any("root_cause" in m for m in missing))
        self.assertIn("DRAFT", text)
        self.assertIn("Completeness checklist", text)

    def test_p1_without_five_whys_is_draft(self):
        incident = dict(BASE)
        incident.pop("five_whys")
        _, missing = rca_generator.render(incident, rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertTrue(any("five_whys" in m for m in missing))

    def test_p3_without_five_whys_is_not_draft(self):
        # P2/P3 RCAs are allowed to omit the 5-whys chain.
        incident = dict(BASE)
        incident["priority"] = "P3"
        incident.pop("five_whys")
        _, missing = rca_generator.render(incident, rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertFalse(any("five_whys" in m for m in missing))

    def test_action_item_missing_owner_flagged(self):
        incident = json.loads(json.dumps(BASE))
        incident["action_items"][0].pop("owner")
        _, missing = rca_generator.render(incident, rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertTrue(any("action item 1" in m for m in missing))

    def test_shallow_five_whys_flagged(self):
        incident = dict(BASE)
        incident["five_whys"] = ["Why 1.", "Why 2."]
        _, missing = rca_generator.render(incident, rca_generator.DEFAULT_TEMPLATE, "2026-11-24 11:00")
        self.assertTrue(any("too shallow" in m for m in missing))


class TestTimeline(unittest.TestCase):
    def test_elapsed_minutes_computed(self):
        rows = rca_generator.build_timeline_rows(BASE)
        self.assertIn("| 2026-11-24T09:45 | 45m | Fix applied |", rows)
        self.assertIn("| 2026-11-24T10:30 | 1h 30m | Resolved |", rows)

    def test_fmt_duration(self):
        self.assertEqual(rca_generator.fmt_duration(105), "1h 45m")
        self.assertEqual(rca_generator.fmt_duration(33), "33m")
        self.assertEqual(rca_generator.fmt_duration(None), "—")


class TestCli(unittest.TestCase):
    def test_cli_final_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_incident(BASE, tmp)
            out = Path(tmp) / "rca.md"
            rc = rca_generator.main([str(path), "--out", str(out), "--generated-at", "2026-11-24 11:00"])
            self.assertEqual(rc, 0)
            self.assertIn("INC-9999", out.read_text())

    def test_cli_draft_exit_one(self):
        incident = dict(BASE)
        incident.pop("root_cause")
        with tempfile.TemporaryDirectory() as tmp:
            path = write_incident(incident, tmp)
            out = Path(tmp) / "rca.md"
            rc = rca_generator.main([str(path), "--out", str(out)])
            self.assertEqual(rc, 1)
            self.assertIn("DRAFT", out.read_text())

    def test_cli_bad_json_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{ not json")
            self.assertEqual(rca_generator.main([str(path)]), 2)

    def test_cli_missing_file_exit_two(self):
        self.assertEqual(rca_generator.main(["/nonexistent/incident.json"]), 2)


if __name__ == "__main__":
    unittest.main()
