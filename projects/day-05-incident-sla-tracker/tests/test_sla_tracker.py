import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sla_tracker import analyse, assess, build_report, exit_code, load_incidents

NOW = datetime(2026, 11, 11, 9, 20)


class TestSlaTracker(unittest.TestCase):
    def setUp(self):
        self.sample = Path(__file__).resolve().parents[1] / "sample_data" / "incidents.csv"
        self.incidents = load_incidents(self.sample)
        self.result = analyse(self.incidents, NOW)

    def test_parses_all_sample_rows(self):
        self.assertEqual(len(self.incidents), 11)

    def test_breached_tickets_detected(self):
        breached = {e["ticket_id"] for e in self.result["breached"]}
        self.assertEqual(breached, {"INC-1042", "INC-1047", "INC-1050"})

    def test_at_risk_tickets_detected(self):
        at_risk = {e["ticket_id"] for e in self.result["at_risk"]}
        self.assertEqual(at_risk, {"INC-1043", "INC-1044"})

    def test_on_track_and_closed_counts(self):
        self.assertEqual(len(self.result["on_track"]), 5)
        self.assertEqual(len(self.result["closed"]), 1)
        self.assertEqual(self.result["closed"][0]["ticket_id"], "INC-1041")

    def test_breached_means_exit_code_2(self):
        self.assertEqual(exit_code(self.result), 2)

    def test_p1_deadline_is_4_hours_after_creation(self):
        inc = next(i for i in self.incidents if i["ticket_id"] == "INC-1042")
        deadline, remaining, state = assess(inc, NOW)
        self.assertEqual(deadline, datetime(2026, 11, 11, 8, 30))
        self.assertEqual(state, "BREACHED")

    def test_report_names_breaches_and_next_risk(self):
        report = build_report(self.incidents, self.result, NOW, "incidents.csv")
        self.assertIn("Incident SLA Report", report)
        self.assertIn("INC-1042", report)
        self.assertIn("INC-1043", report)
        self.assertIn("BREACH", report)

    def test_unknown_priority_is_flagged_not_crashed(self):
        weird = {"ticket_id": "INC-9999", "summary": "Odd one", "priority": "P9",
                 "status": "Open", "assignee": "Nobody",
                 "created": datetime(2026, 11, 11, 8, 0)}
        result = analyse([weird], NOW)
        self.assertEqual(len(result["unknown"]), 1)


if __name__ == "__main__":
    unittest.main()
