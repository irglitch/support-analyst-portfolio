"""Tests for Day 09 — Database Lock / Slow Session Checker."""
import sys
import tempfile
import unittest
from pathlib import Path

# Allow running from the repo root as well as from the project folder.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import session_checker

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
SAMPLE = PROJECT / "sample_data" / "sessions.csv"

HEADER = ("session_id,username,application,state,query,wait_event,"
          "duration_seconds,blocking_session_id\n")


def write_csv(rows):
    """Write rows (list of CSV lines, no header) to a temp file; return path."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                     newline="", encoding="utf-8")
    fh.write(HEADER)
    fh.write("\n".join(rows) + "\n")
    fh.close()
    return fh.name


def run_on_rows(rows):
    path = write_csv(rows)
    try:
        return session_checker.check(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestSampleData(unittest.TestCase):
    def test_headline_totals(self):
        report, _ = session_checker.check(str(SAMPLE))
        self.assertIn("**Sessions in snapshot:** 14", report)
        self.assertIn("**Active:** 7", report)
        self.assertIn("**Blocked:** 4", report)
        self.assertIn("**Longest-running session:** 2h 0m", report)

    def test_blocking_chain_found(self):
        report, n_issues = session_checker.check(str(SAMPLE))
        # SESS-101 (overnight settlement, 42 min) blocks 3 sessions;
        # SESS-102 (idle in transaction, 18 min) blocks 1.
        self.assertIn("🔴 BLOCKING CHAIN", report)
        self.assertIn("2 blocker session(s)", report)
        self.assertIn("4 session(s)", report)
        self.assertIn("SESS-101", report)
        self.assertIn("SESS-102", report)
        self.assertGreater(n_issues, 0)

    def test_blocked_sessions_listed(self):
        report, _ = session_checker.check(str(SAMPLE))
        for sid in ("SESS-104", "SESS-105", "SESS-107", "SESS-108"):
            self.assertIn(sid, report)
        # Longest waiter: SESS-104 at 640s = 10m 40s.
        self.assertIn("10m 40s", report)

    def test_long_running_sessions_flagged(self):
        report, _ = session_checker.check(str(SAMPLE))
        long_section = report.split("## 3.")[1].split("## 4.")[0]
        self.assertIn("SESS-101", long_section)  # 42m 0s
        self.assertIn("SESS-103", long_section)  # 12m 0s, reporting query
        # SESS-102 (18m 0s) is idle in transaction, not active — it belongs
        # in section 4, not here.
        self.assertNotIn("SESS-102", long_section)
        self.assertNotIn("SESS-112", long_section)  # 6m 20s — watch list only

    def test_idle_in_transaction_flagged(self):
        report, _ = session_checker.check(str(SAMPLE))
        idle_section = report.split("## 4.")[1].split("## 5.")[0]
        self.assertIn("SESS-102", idle_section)
        self.assertNotIn("SESS-115", idle_section)  # 45s, under threshold

    def test_watch_list(self):
        report, _ = session_checker.check(str(SAMPLE))
        watch_section = report.split("## 5.")[1].split("## What")[0]
        self.assertIn("SESS-112", watch_section)  # 6m 20s
        self.assertIn("SESS-114", watch_section)  # 2m 10s
        self.assertNotIn("SESS-109", watch_section)  # 3s, normal

    def test_harmless_sessions_not_flagged(self):
        report, _ = session_checker.check(str(SAMPLE))
        # SESS-110 is idle 2h but holds no locks — named only in the
        # "not flagged" section, never in a flagged table.
        flagged = report.split("## What was checked")[0]
        self.assertNotIn("SESS-110", flagged)


class TestCleanData(unittest.TestCase):
    def test_no_issues_is_healthy(self):
        rows = [
            'SESS-201,app-user,checkout-api,active,"SELECT * FROM products",,5,',
            'SESS-202,app-user,checkout-api,idle,,,3600,',
            'SESS-203,batch-user,reporting,active,"SELECT COUNT(*) FROM sales",,90,',
        ]
        report, n_issues = run_on_rows(rows)
        self.assertEqual(n_issues, 0)
        self.assertIn("✅ HEALTHY", report)
        self.assertIn("**Sessions in snapshot:** 3", report)

    def test_slow_but_not_blocking_is_warning(self):
        rows = [
            'SESS-201,report-user,reporting,active,"SELECT * FROM sales",,900,',
        ]
        report, n_issues = run_on_rows(rows)
        self.assertEqual(n_issues, 1)
        self.assertIn("⚠️ SLOW SESSIONS", report)
        self.assertNotIn("🔴 BLOCKING CHAIN", report)

    def test_single_blocker_counts_once(self):
        rows = [
            'SESS-201,batch-user,batch,active,"UPDATE t SET x=1",,1800,',
            'SESS-202,app-user,checkout-api,blocked,"INSERT INTO t VALUES (1)",row lock,300,SESS-201',
            'SESS-203,app-user,checkout-api,blocked,"UPDATE t SET x=2",row lock,120,SESS-201',
        ]
        report, n_issues = run_on_rows(rows)
        self.assertIn("🔴 BLOCKING CHAIN", report)
        self.assertIn("1 blocker session(s)", report)
        self.assertIn("2 session(s)", report)
        self.assertIn("5m 0s", report)  # longest waiter SESS-202

    def test_bad_duration_raises(self):
        rows = [
            'SESS-201,app-user,checkout-api,active,"SELECT 1",,not-a-number,',
        ]
        with self.assertRaises(ValueError):
            run_on_rows(rows)


class TestFmtDuration(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(session_checker.fmt_duration(45), "45s")
        self.assertEqual(session_checker.fmt_duration(130), "2m 10s")
        self.assertEqual(session_checker.fmt_duration(2520), "42m 0s")
        self.assertEqual(session_checker.fmt_duration(7200), "2h 0m")


if __name__ == "__main__":
    unittest.main()
