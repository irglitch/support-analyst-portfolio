import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from error_kb import (build_search_report, filter_system, kb_stats,
                      load_kb, score_entry, search_kb)

KB = Path(__file__).resolve().parents[1] / "sample_data" / "knowledge_base.json"


class TestErrorKb(unittest.TestCase):
    def setUp(self):
        self.entries = load_kb(KB)
        self.by_code = {e["code"]: e for e in self.entries}

    def test_loads_all_sample_entries(self):
        self.assertEqual(len(self.entries), 12)
        self.assertEqual(len({e["code"] for e in self.entries}), 12)

    def test_every_entry_has_all_required_fields(self):
        required = ("code", "system", "symptom", "cause", "fix",
                    "ticket", "resolved", "times_seen", "severity")
        for entry in self.entries:
            for field in required:
                self.assertIn(field, entry, f"{entry['code']} missing {field}")

    def test_exact_code_match_ranks_first(self):
        matches = search_kb(self.entries, "ORA-12154")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0]["code"], "ORA-12154")
        self.assertEqual(matches[0][1], 100)

    def test_search_is_case_insensitive(self):
        matches = search_kb(self.entries, "ora-12154")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0]["code"], "ORA-12154")

    def test_timeout_keyword_finds_three_entries(self):
        matches = search_kb(self.entries, "timeout")
        codes = [e["code"] for e, _ in matches]
        self.assertEqual(codes, ["PAY-3002", "DB-1045", "RPT-207"])
        # All three are keyword hits, so the most-seen comes first.
        self.assertEqual(matches[0][0]["times_seen"], 6)

    def test_code_substring_outranks_keyword(self):
        # "HTTP" is part of two codes; the keyword "gateway" only hits PAY-3002.
        http_matches = search_kb(self.entries, "HTTP")
        self.assertEqual([e["code"] for e, _ in http_matches],
                         ["HTTP-500", "HTTP-502"])
        self.assertTrue(all(s == 50 for _, s in http_matches))
        self.assertEqual(search_kb(self.entries, "gateway")[0][0]["code"],
                         "PAY-3002")

    def test_unknown_query_returns_no_matches(self):
        self.assertEqual(search_kb(self.entries, "zzzz-not-a-code"), [])

    def test_symptom_keyword_finds_settlement_entry(self):
        matches = search_kb(self.entries, "settlement")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0]["code"], "SFTP-550")
        self.assertIn("550", matches[0][0]["symptom"])

    def test_system_filter_lists_crm_entries(self):
        crm = filter_system(self.entries, "CRM")
        self.assertEqual([e["code"] for e in crm], ["AUTH-401", "SYNC-409"])
        self.assertEqual(filter_system(self.entries, "crm")[0]["code"],
                         "AUTH-401")  # case-insensitive
        self.assertEqual(filter_system(self.entries, "No Such System"), [])

    def test_stats_totals(self):
        stats = kb_stats(self.entries)
        self.assertEqual(stats["entries"], 12)
        self.assertEqual(stats["systems"], 8)
        self.assertEqual(stats["total_seen"], 44)
        self.assertEqual(stats["by_severity"], {"P1": 3, "P2": 4, "P3": 5})
        self.assertEqual(stats["most_seen"][0]["code"], "PAY-3002")
        self.assertEqual(stats["most_seen"][0]["times_seen"], 6)

    def test_report_names_the_match_and_its_fix(self):
        matches = search_kb(self.entries, "ORA-12154")
        report = build_search_report("ORA-12154", matches, "knowledge_base.json")
        self.assertIn("ORA-12154", report)
        self.assertIn("tnsnames.ora", report)
        self.assertIn("INC-0987", report)
        self.assertIn("Matches:** 1", report)

    def test_report_for_no_match_says_what_to_do_next(self):
        report = build_search_report("zzzz", [], "knowledge_base.json")
        self.assertIn("No entry matches", report)
        self.assertIn("try a shorter word", report)

    def test_bad_json_raises_value_error(self):
        bad = Path(__file__).resolve().parent / "bad_kb.json"
        bad.write_text("{not valid json", encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_kb(bad)
        finally:
            bad.unlink()

    def test_entry_missing_a_field_raises_value_error(self):
        bad = Path(__file__).resolve().parent / "incomplete_kb.json"
        bad.write_text('[{"code": "X-1", "system": "Web"}]', encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_kb(bad)
        finally:
            bad.unlink()


if __name__ == "__main__":
    unittest.main()
