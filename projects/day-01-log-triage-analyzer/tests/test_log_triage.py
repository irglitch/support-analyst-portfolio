import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from log_triage import build_report, parse_log, suggest_priority
from collections import Counter


class TestLogTriage(unittest.TestCase):
    def setUp(self):
        self.sample = Path(__file__).resolve().parents[1] / "sample_data" / "app.log"
        self.entries, self.unparsed = parse_log(self.sample)

    def test_parses_all_sample_lines(self):
        self.assertEqual(self.unparsed, 0)
        self.assertGreater(len(self.entries), 20)

    def test_dominant_error_is_db_timeout(self):
        errors = [e for e in self.entries if e["level"] in ("ERROR", "FATAL")]
        codes = Counter(e["code"] for e in errors)
        self.assertEqual(codes.most_common(1)[0][0], "DB_CONN_TIMEOUT")

    def test_db_timeout_suggests_p1(self):
        priority, _ = suggest_priority(Counter({"DB_CONN_TIMEOUT": 3}))
        self.assertIn("P1", priority)

    def test_report_mentions_top_service(self):
        report = build_report(self.entries, self.unparsed, "app.log")
        self.assertIn("payment-api", report)
        self.assertIn("Incident Triage Report", report)


if __name__ == "__main__":
    unittest.main()
