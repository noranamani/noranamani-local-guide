"""Deterministic JST quota gate for a backup cron, without HTTP."""
import unittest

from localguide.core import GuideError, parse_time
from scripts.refresh_fallback_gate import should_proceed


class FallbackGateTests(unittest.TestCase):
    def setUp(self):
        self.now = parse_time("2026-11-16T17:17:00+09:00")
        self.current = {"id": 300, "event": "schedule", "created_at": "2026-11-16T08:17:00Z"}

    def test_no_primary_attempt_allows_backup(self):
        self.assertTrue(should_proceed([self.current], self.now, 300))

    def test_any_primary_run_blocks_backup_even_on_failure(self):
        for status in ("success", "failure", "queued", "in_progress"):
            primary = {"id": 299, "event": "schedule", "created_at": "2026-11-15T23:25:00Z",
                       "conclusion": status}
            with self.subTest(status=status):
                self.assertFalse(should_proceed([self.current, primary], self.now, 300))

    def test_manual_dispatch_also_blocks_backup(self):
        earlier = {"id": 299, "event": "workflow_dispatch", "created_at": "2026-11-16T04:00:00Z"}
        self.assertFalse(should_proceed([self.current, earlier], self.now, 300))

    def test_yesterday_does_not_block_and_current_run_must_be_listed(self):
        yesterday = {"id": 299, "event": "schedule", "created_at": "2026-11-15T01:17:00Z"}
        self.assertTrue(should_proceed([self.current, yesterday], self.now, 300))
        with self.assertRaises(GuideError):
            should_proceed([yesterday], self.now, 300)


if __name__ == "__main__":
    unittest.main()
