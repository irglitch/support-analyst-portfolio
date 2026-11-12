import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lockout_triage import (build_report, exit_code, load_accounts,
                            load_attempts, triage_all, triage_user)

NOW = datetime(2026, 11, 12, 9, 20)


class TestLockoutTriage(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[1] / "sample_data"
        self.accounts = load_accounts(base / "accounts.csv")
        self.attempts = load_attempts(base / "login_attempts.csv")
        self.results = triage_all(self.accounts, self.attempts, NOW)
        self.by_user = {r["username"]: r for r in self.results}

    def test_parses_all_sample_rows(self):
        self.assertEqual(len(self.accounts), 7)
        self.assertEqual(len(self.attempts), 15)

    def test_priya_is_locked_with_five_failures_first(self):
        r = self.by_user["priya.k"]
        self.assertEqual(r["cause"], "LOCKED")
        self.assertTrue(r["needs_admin"])
        self.assertEqual(r["failures"], 5)
        self.assertTrue(any("Mobile mail app" in e for e in r["evidence"]))

    def test_sam_password_expired_not_locked(self):
        r = self.by_user["sam.r"]
        self.assertEqual(r["cause"], "EXPIRED")
        self.assertFalse(r["needs_admin"])
        self.assertTrue(any("2026-11-11" in e for e in r["evidence"]))

    def test_ana_mfa_failing_after_correct_password(self):
        r = self.by_user["ana.m"]
        self.assertEqual(r["cause"], "MFA")
        self.assertFalse(r["needs_admin"])
        self.assertTrue(any("MFA failure" in e for e in r["evidence"]))

    def test_chen_disabled_needs_admin(self):
        r = self.by_user["chen.l"]
        self.assertEqual(r["cause"], "DISABLED")
        self.assertTrue(r["needs_admin"])
        self.assertIn("Do NOT re-enable", r["action"])

    def test_jordan_password_expiring_in_three_days(self):
        r = self.by_user["jordan.p"]
        self.assertEqual(r["cause"], "EXPIRING_SOON")
        self.assertTrue(any("3 day" in e for e in r["evidence"]))

    def test_alex_resolved_and_mia_no_attempts(self):
        self.assertEqual(self.by_user["alex.d"]["cause"], "RESOLVED")
        self.assertEqual(self.by_user["mia.t"]["cause"], "NO_ATTEMPTS")
        self.assertFalse(self.by_user["alex.d"]["needs_admin"])
        self.assertFalse(self.by_user["mia.t"]["needs_admin"])

    def test_admin_action_needed_means_exit_code_2(self):
        self.assertEqual(exit_code(self.results), 2)

    def test_single_user_filter(self):
        one = triage_all(self.accounts, self.attempts, NOW, username="sam.r")
        self.assertEqual(len(one), 1)
        self.assertEqual(one[0]["cause"], "EXPIRED")

    def test_report_names_every_cause(self):
        report = build_report(self.results, NOW,
                              ["accounts.csv", "login_attempts.csv"])
        for name in ("priya.k", "sam.r", "ana.m", "chen.l", "jordan.p",
                     "alex.d", "mia.t"):
            self.assertIn(name, report)
        self.assertIn("Account Lockout Triage Report", report)
        self.assertIn("ADMIN ACTION NEEDED", report)

    def test_repeated_failures_before_lock_flagged(self):
        # A user with 5 failures in the last hour but no lock flag yet.
        account = {"username": "test.u", "full_name": "Test User",
                   "status": "active",
                   "password_expiry": datetime(2026, 12, 31).date(),
                   "mfa_enabled": False,
                   "last_login": datetime(2026, 11, 11, 9, 0)}
        attempts = [{"timestamp": datetime(2026, 11, 12, 9, 0) + __import__("datetime").timedelta(minutes=i * 5),
                     "username": "test.u", "result": "failure",
                     "reason": "bad password", "source": "Office laptop"}
                    for i in range(5)]
        r = triage_user(account, attempts, NOW)
        self.assertEqual(r["cause"], "REPEATED_FAILURES")
        self.assertIn("STOP retrying", r["action"])


if __name__ == "__main__":
    unittest.main()
