"""Checks that a Jira ticket never carries reviewer names.

    python -m unittest
"""
import unittest
from unittest.mock import patch

from core.config import settings
from core.database import Review
from core.jira_client import JiraClient

REVIEWER_NAME = "Zephyrine Quillfeather"


def all_keys(value):
    """Every dict key in a nested payload, at any depth."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from all_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from all_keys(child)


class JiraPayloadTest(unittest.TestCase):
    def setUp(self):
        jira_settings = {
            "JIRA_URL": "https://example.atlassian.net",
            "JIRA_EMAIL": "triage@example.com",
            "JIRA_API_TOKEN": "test-token",
        }
        for key, value in jira_settings.items():
            patcher = patch.object(settings, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        # Stand-in for the JIRA library, so no network call is made and the payload can be inspected.
        jira_patcher = patch("core.jira_client.JIRA")
        self.jira = jira_patcher.start().return_value
        self.addCleanup(jira_patcher.stop)

        reviews = [
            Review(review_id="r1", reviewer_name=REVIEWER_NAME, rating=1, review_text="Crashes on the loading screen"),
            Review(review_id="r2", reviewer_name="Player 2", rating=2, review_text="Black screen after the update"),
        ]
        JiraClient().create_bug_ticket("Crash on Startup", 20.0, reviews)
        self.fields = self.jira.create_issue.call_args.kwargs["fields"]

    def test_payload_has_no_reviewer_name_field(self):
        self.assertNotIn("reviewer_name", set(all_keys(self.fields)))

    def test_reviewer_name_does_not_appear_in_any_value(self):
        self.assertNotIn(REVIEWER_NAME, str(self.fields))
        self.assertNotIn("Player 2", str(self.fields))

    def test_review_text_still_reaches_the_ticket(self):
        self.assertIn("Crashes on the loading screen", self.fields["description"])
