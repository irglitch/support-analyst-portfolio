import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sla_early_warning import assess, assess_all, fmt_minutes

NOW = datetime(2026, 11, 28, 9, 20)


def ticket(**overrides):
    base = {
        "ticket_id": "INC-T", "summary": "Test ticket", "priority": "P2",
        "status": "In Progress", "assignee": "Sam R",
        "created": "2026-11-28T04:00", "last_update": "2026-11-28T09:00",
        "progress_percent": 50, "estimated_remaining_minutes": 30,
        "blocked_on": None,
    }
    base.update(overrides)
    return base


class EarlyWarningTests(unittest.TestCase):
    def test_forecast_breach_before_deadline(self):
        # 40m of clock left, 90m of work remaining -> will breach.
        result = assess(ticket(priority="P1",
                               created="2026-11-28T05:40",
                               estimated_remaining_minutes=90), NOW)
        self.assertEqual(result["level"], "WILL BREACH")

    def test_already_breached(self):
        result = assess(ticket(created="2026-11-27T23:00"), NOW)
        self.assertEqual(result["level"], "BREACHED")

    def test_stale_and_unassigned_raise_at_risk(self):
        stale = assess(ticket(last_update="2026-11-27T13:00",
                              priority="P3",
                              created="2026-11-27T12:00"), NOW)
        self.assertEqual(stale["level"], "AT RISK")
        unassigned = assess(ticket(assignee=None), NOW)
        self.assertEqual(unassigned["level"], "AT RISK")

    def test_on_track_and_closed_excluded(self):
        results, closed, _ = assess_all(
            [ticket(), ticket(ticket_id="INC-C", status="Resolved")], NOW)
        self.assertEqual(results[0]["level"], "ON TRACK")
        self.assertEqual(len(closed), 1)

    def test_fmt_minutes(self):
        self.assertEqual(fmt_minutes(140), "2h 20m")
        self.assertEqual(fmt_minutes(45), "45m")


if __name__ == "__main__":
    unittest.main()
