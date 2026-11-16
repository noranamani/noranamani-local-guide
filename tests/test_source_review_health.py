"""Deterministic renewal tests; no network access or date extension."""
import unittest
from datetime import timedelta

from localguide.core import parse_time
from scripts.source_review_health import inspect_sources


class SourceReviewHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = parse_time("2026-11-16T12:00:00+09:00")
        self.source = {"id": "fixture", "enabled": True, "checked_at": self.now.isoformat()}

    def test_valid_and_warning_states(self):
        config = {"sources": [self.source]}
        notices, expired = inspect_sources(config, self.now)
        self.assertEqual(notices[0][1], "valid")
        self.assertFalse(expired)
        notices, expired = inspect_sources(config, self.now + timedelta(days=24))
        self.assertEqual(notices[0][1], "due_soon")
        self.assertFalse(expired)

    def test_expired_does_not_extend_permissions(self):
        config = {"sources": [self.source, {"id": "inactive", "enabled": False}]}
        reviewed = self.source["checked_at"]
        notices, expired = inspect_sources(config, self.now + timedelta(days=31))
        self.assertTrue(expired)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0][1], "expired")
        self.assertEqual(reviewed, self.source["checked_at"])


if __name__ == "__main__":
    unittest.main()
