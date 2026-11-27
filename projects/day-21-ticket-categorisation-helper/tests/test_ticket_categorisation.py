#!/usr/bin/env python3
"""Tests for the Day 21 Ticket Categorisation Helper (stdlib unittest)."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ticket_categorisation

BASE = {
    "ticket_id": "TKT-9999",
    "subject": "Password reset for new starter",
    "description": "Password reset and account setup for a new starter.",
    "service": "identity",
    "current_category": "Access Request",
    "current_priority": "P4",
    "affected_users": 1,
}


def fresh(**overrides):
    ticket = copy.deepcopy(BASE)
    ticket.update(overrides)
    return ticket


class TestCategorisation(unittest.TestCase):
    def test_correct_ticket_needs_no_action(self):
        result = ticket_categorisation.categorise_ticket(fresh())
        self.assertEqual(result["suggested_category"], "Access Request")
        self.assertEqual(result["suggested_priority"], "P4")
        self.assertEqual(result["actions"], [])
        self.assertFalse(result["needs_review"])

    def test_hidden_p1_is_flagged(self):
        ticket = fresh(
            subject="Checkout returns 500 for all customers",
            description="Nobody can complete a purchase; revenue is stopped.",
            service="checkout-api",
            current_category="General",
            current_priority="P3",
            affected_users=1200,
        )
        result = ticket_categorisation.categorise_ticket(ticket)
        self.assertEqual(result["suggested_priority"], "P1")
        self.assertTrue(any("hidden P1" in a for a in result["actions"]))
        self.assertTrue(any("Re-categorise" in a for a in result["actions"]))

    def test_vague_ticket_goes_to_human_review(self):
        ticket = fresh(subject="System slow", description="System is slow today.",
                       service="", current_category="General",
                       current_priority="P3")
        result = ticket_categorisation.categorise_ticket(ticket)
        self.assertTrue(result["needs_review"])
        self.assertIsNone(result["suggested_category"])
        self.assertTrue(any("human review" in a for a in result["actions"]))

    def test_settlement_file_is_batch_not_app_error(self):
        ticket = fresh(
            subject="Settlement file missing again",
            description="The settlement file did not arrive over SFTP; "
                        "the batch is blocking, deadline today.",
            service="settlement-service",
            current_category="Incident — Application Error",
            current_priority="P3",
            affected_users=25,
        )
        result = ticket_categorisation.categorise_ticket(ticket)
        self.assertEqual(result["suggested_category"], "Batch & File Transfer")
        self.assertEqual(result["suggested_priority"], "P2")

    def test_certificate_expiry_is_p2_not_p1(self):
        # Many users affected, but nothing is down yet — urgent, not P1.
        ticket = fresh(
            subject="Portal certificate expires Monday",
            description="The TLS certificate expires Monday; the live "
                        "endpoint still shows the old expiry.",
            service="customer-portal",
            current_category="Certificate & Security",
            current_priority="P3",
            affected_users=500,
        )
        result = ticket_categorisation.categorise_ticket(ticket)
        self.assertEqual(result["suggested_category"], "Certificate & Security")
        self.assertEqual(result["suggested_priority"], "P2")

    def test_priority_can_be_lowered(self):
        ticket = fresh(current_priority="P2")
        result = ticket_categorisation.categorise_ticket(ticket)
        self.assertTrue(any("Lower priority: P2 → P4" in a
                            for a in result["actions"]))


class TestDuplicates(unittest.TestCase):
    def test_shared_error_code_flags_duplicate(self):
        first = fresh(ticket_id="TKT-1", service="checkout-api",
                      subject="Checkout 500 errors",
                      description="Gateway timeout PAY-3002 on checkout.")
        second = fresh(ticket_id="TKT-2", service="checkout-api",
                       subject="Checkout failing",
                       description="Seeing PAY-3002 repeatedly.")
        duplicates = ticket_categorisation.find_duplicates([first, second])
        self.assertEqual(len(duplicates), 1)
        self.assertIn("PAY-3002", duplicates[0][2])

    def test_different_services_are_not_duplicates(self):
        first = fresh(ticket_id="TKT-1", service="checkout-api",
                      subject="Checkout 500 errors",
                      description="Gateway timeout PAY-3002.")
        second = fresh(ticket_id="TKT-2", service="billing-api",
                       subject="Checkout 500 errors",
                       description="Gateway timeout PAY-3002.")
        self.assertEqual(ticket_categorisation.find_duplicates([first, second]), [])


class TestReport(unittest.TestCase):
    def test_clean_queue_reports_no_actions(self):
        results = [ticket_categorisation.categorise_ticket(fresh())]
        report, action_count = ticket_categorisation.build_report(
            results, [], "2026-11-27 09:20")
        self.assertEqual(action_count, 0)
        self.assertIn("Queue clean", report)


if __name__ == "__main__":
    unittest.main()
