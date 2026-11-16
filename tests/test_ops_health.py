"""Offline tests for the automatic issue/health evaluation."""
import unittest
from datetime import timedelta

from localguide.core import parse_time
from scripts.ops_health import assess


class OperationsHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = parse_time("2026-11-16T22:47:00+09:00")
        self.checked = self.now - timedelta(days=1)
        self.config = {"sources": [{"id": "akashi_open_data", "enabled": True,
                                    "checked_at": self.checked.isoformat()}]}
        self.state = {"sources": {"akashi_open_data": {
            "last_success_at": (self.now - timedelta(hours=8)).isoformat(),
            "attempt_day": self.now.date().isoformat(),
            "last_error": None, "halted": False,
        }}}

    def test_recent_success_healthy(self):
        self.assertEqual(assess(self.now, self.config, self.state), [])

    def test_timeout_and_failed_daily_attempt_detected(self):
        record = self.state["sources"]["akashi_open_data"]
        record["last_success_at"] = (self.now - timedelta(hours=41)).isoformat()
        record["last_error"] = "Safe error"
        self.assertIn("daily_success_stale", assess(self.now, self.config, self.state))
        self.assertIn("daily_attempt_failed", assess(self.now, self.config, self.state))

    def test_access_halt_and_failed_workflow(self):
        self.state["sources"]["akashi_open_data"]["halted"] = True
        codes = assess(self.now, self.config, self.state, "failure")
        self.assertEqual(codes, ["access_halted", "workflow_failure"])

    def test_review_warning_expiry_and_never_success(self):
        self.config["sources"][0]["checked_at"] = (self.now - timedelta(days=25)).isoformat()
        self.assertIn("source_review_due_soon", assess(self.now, self.config, self.state))
        self.config["sources"][0]["checked_at"] = (self.now - timedelta(days=31)).isoformat()
        self.assertIn("source_review_expired", assess(self.now, self.config, self.state))
        self.state["sources"]["akashi_open_data"].pop("last_success_at")
        self.assertIn("never_succeeded", assess(self.now, self.config, self.state))

    def test_invalid_health_timestamps_are_reported(self):
        self.state["sources"]["akashi_open_data"]["last_success_at"] = "invalid"
        self.state["sources"]["akashi_open_data"]["last_error"] = "safe failure"
        self.assertIn("invalid_success_timestamp",
                      assess(self.now, self.config, self.state))
        self.config["sources"][0]["checked_at"] = "invalid"
        self.assertIn("source_review_invalid", assess(self.now, self.config, self.state))

    def test_bad_source_config_is_reported(self):
        self.assertIn("source_configuration",
                      assess(self.now, {"sources": None}, self.state))
        self.assertIn("source_configuration",
                      assess(self.now, {"sources": ["bad"]}, self.state))

    def test_missing_or_corrupted_state_is_not_reported_healthy(self):
        self.assertIn("never_succeeded",
                      assess(self.now, self.config, {"sources": {}}))
        self.assertIn("state_invalid",
                      assess(self.now, self.config, {"sources": []}))

    def test_future_timestamps_cannot_hide_outages(self):
        self.state["sources"]["akashi_open_data"]["last_success_at"] = (
            self.now + timedelta(minutes=1)).isoformat()
        self.assertIn("future_success_timestamp", assess(self.now, self.config, self.state))


if __name__ == "__main__":
    unittest.main()
