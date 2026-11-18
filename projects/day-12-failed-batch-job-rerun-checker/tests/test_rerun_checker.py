#!/usr/bin/env python3
"""Tests for Day 12 — Failed Batch Job Re-Run Checker."""
import csv
import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rerun_checker as rc

HERE = Path(__file__).resolve().parent.parent
SAMPLE = HERE / "sample_data"


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


class TestSampleData(unittest.TestCase):
    def test_sample_verdict_is_safe_resume(self):
        runs = rc.load_history(SAMPLE / "job_history.csv", "SETTLE_NIGHTLY")
        log = (SAMPLE / "job_log.txt").read_text(encoding="utf-8")
        count, total = rc.load_posted(SAMPLE / "posted_transactions.csv")
        downstream = rc.load_downstream(SAMPLE / "downstream_jobs.csv",
                                        "SETTLE_NIGHTLY")
        status = rc.load_status(SAMPLE / "job_status.json")
        result = rc.check_rerun("SETTLE_NIGHTLY", runs, log, count, total,
                                downstream, status)
        self.assertEqual(result["verdict"], "SAFE TO RE-RUN")
        self.assertTrue(result["resume"])
        self.assertEqual(result["posted_count"], 642)
        self.assertEqual(result["posted_total"], Decimal("156594.61"))
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["cause"], "transient")

    def test_sample_report_names_resume_row(self):
        runs = rc.load_history(SAMPLE / "job_history.csv", "SETTLE_NIGHTLY")
        log = (SAMPLE / "job_log.txt").read_text(encoding="utf-8")
        count, total = rc.load_posted(SAMPLE / "posted_transactions.csv")
        downstream = rc.load_downstream(SAMPLE / "downstream_jobs.csv",
                                        "SETTLE_NIGHTLY")
        status = rc.load_status(SAMPLE / "job_status.json")
        result = rc.check_rerun("SETTLE_NIGHTLY", runs, log, count, total,
                                downstream, status)
        report = rc.render_report(result, "SETTLE_NIGHTLY")
        self.assertIn("row 643", report)
        self.assertIn("$156,594.61", report)
        self.assertIn("558 from the re-run", report)


class TestClassifyFailure(unittest.TestCase):
    def test_timeout_is_transient(self):
        cause, _ = rc.classify_failure("ERROR DB connection timeout after 30s")
        self.assertEqual(cause, "transient")

    def test_duplicate_key_is_data(self):
        cause, _ = rc.classify_failure("ERROR duplicate key violates constraint")
        self.assertEqual(cause, "data")

    def test_bad_amount_is_data(self):
        cause, _ = rc.classify_failure("ERROR invalid amount for TXN-1")
        self.assertEqual(cause, "data")

    def test_permission_denied_is_config(self):
        cause, _ = rc.classify_failure("FATAL permission denied opening config")
        self.assertEqual(cause, "config")

    def test_unrecognised_log_is_unknown(self):
        cause, _ = rc.classify_failure("INFO job started\nINFO job ended")
        self.assertEqual(cause, "unknown")


class TestBlockers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.history = self.dir / "history.csv"
        self.posted = self.dir / "posted.csv"
        self.downstream = self.dir / "downstream.csv"
        self.status_file = self.dir / "status.json"
        write_csv(self.history,
                  ["job_id", "run_id", "started_at", "ended_at", "status",
                   "exit_code", "rows_processed", "rows_total",
                   "failure_reason"],
                  [["JOBX", "2026-11-17-0200", "2026-11-17 02:00:00",
                    "2026-11-17 02:47:12", "FAILED", "3", "10", "100",
                    "timeout"]])
        write_csv(self.posted,
                  ["txn_id", "customer_id", "amount", "currency", "txn_date",
                   "account_no", "status"],
                  [["TXN-1", "C1", "10.00", "CAD", "2026-11-17", "A1",
                    "posted"]])
        write_csv(self.downstream,
                  ["job_id", "depends_on", "status", "started_at", "notes"],
                  [["DOWN1", "JOBX", "PENDING", "", ""]])
        self.status_file.write_text(json.dumps({
            "job_id": "JOBX", "lock_held": False, "lock_holder": None,
            "input_file": "in.csv", "input_file_present": True,
            "input_checksum_match": True}), encoding="utf-8")
        self.log = "ERROR DB connection timeout after 30s"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **overrides):
        runs = rc.load_history(self.history, "JOBX")
        count, total = rc.load_posted(self.posted)
        downstream = rc.load_downstream(self.downstream, "JOBX")
        status = rc.load_status(self.status_file)
        log = overrides.pop("log", self.log)
        if "status_override" in overrides:
            status.update(overrides.pop("status_override"))
        if "downstream_override" in overrides:
            downstream = overrides.pop("downstream_override")
        if "history_status" in overrides:
            runs[0]["status"] = overrides.pop("history_status")
        return rc.check_rerun("JOBX", runs, log, count, total,
                              downstream, status)

    def test_baseline_is_safe_resume(self):
        result = self._run()
        self.assertEqual(result["verdict"], "SAFE TO RE-RUN")
        self.assertTrue(result["resume"])

    def test_succeeded_job_is_blocked(self):
        result = self._run(history_status="SUCCEEDED")
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")
        self.assertTrue(any("already succeeded" in b for b in result["blockers"]))

    def test_running_job_is_wait(self):
        result = self._run(history_status="RUNNING")
        self.assertEqual(result["verdict"], "WAIT")

    def test_lock_held_is_blocked(self):
        result = self._run(status_override={"lock_held": True,
                                            "lock_holder": "worker-2"})
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")
        self.assertTrue(any("lock" in b.lower() for b in result["blockers"]))

    def test_data_error_is_blocked(self):
        result = self._run(log="ERROR duplicate key violates constraint")
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")
        self.assertTrue(any("data error" in b for b in result["blockers"]))

    def test_downstream_completed_is_blocked(self):
        result = self._run(downstream_override=[
            {"job_id": "DOWN1", "status": "COMPLETED",
             "started_at": "2026-11-17 03:00:00", "notes": ""}])
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")
        self.assertTrue(any("Downstream" in b for b in result["blockers"]))

    def test_missing_input_file_is_blocked(self):
        result = self._run(status_override={"input_file_present": False})
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")

    def test_changed_input_file_is_blocked(self):
        result = self._run(status_override={"input_checksum_match": False})
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")

    def test_unknown_failure_cause_is_blocked(self):
        result = self._run(log="INFO something odd happened")
        self.assertEqual(result["verdict"], "DO NOT RE-RUN")

    def test_no_rows_posted_is_safe_full_run(self):
        self.posted.write_text(
            "txn_id,customer_id,amount,currency,txn_date,account_no,status\n",
            encoding="utf-8")
        result = self._run()
        self.assertEqual(result["verdict"], "SAFE TO RE-RUN")
        self.assertFalse(result["resume"])


class TestCli(unittest.TestCase):
    def test_cli_exit_zero_on_sample(self):
        code = rc.main(["--job", "SETTLE_NIGHTLY",
                        str(SAMPLE / "job_history.csv"),
                        str(SAMPLE / "job_log.txt"),
                        str(SAMPLE / "posted_transactions.csv"),
                        str(SAMPLE / "downstream_jobs.csv"),
                        str(SAMPLE / "job_status.json")])
        self.assertEqual(code, 0)

    def test_cli_exit_two_on_missing_file(self):
        code = rc.main(["--job", "SETTLE_NIGHTLY",
                        str(SAMPLE / "job_history.csv"),
                        str(SAMPLE / "job_log.txt"),
                        str(SAMPLE / "posted_transactions.csv"),
                        str(SAMPLE / "downstream_jobs.csv"),
                        str(SAMPLE / "no_such_file.json")])
        self.assertEqual(code, 2)

    def test_load_history_rejects_unknown_job(self):
        with self.assertRaises(ValueError):
            rc.load_history(SAMPLE / "job_history.csv", "NO_SUCH_JOB")


if __name__ == "__main__":
    unittest.main()
