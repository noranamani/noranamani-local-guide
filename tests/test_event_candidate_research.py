"""Offline regression for discoverable candidate URL seed; never publishes candidates."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from localguide.core import now_jst, safe_url
from localguide.site import create_files
from scripts.event_candidates import add_candidates, read_queue

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "planning/event-candidate-urls-20261027.txt"


class EventCandidateResearchTests(unittest.TestCase):
    def test_seed_contains_25_unique_https_urls(self):
        urls = SEED.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(urls), 25)
        self.assertEqual(len(set(urls)), 25)
        for url in urls:
            self.assertEqual(safe_url(url), url)
        self.assertTrue(any("city.kakogawa.lg.jp" in u for u in urls))
        self.assertTrue(any("city.himeji.lg.jp" in u for u in urls))
        self.assertTrue(any("am12.jp" in u for u in urls))

    def test_seed_is_only_added_to_a_gitignored_offline_queue(self):
        urls = SEED.read_text(encoding="utf-8").splitlines()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
                self.assertEqual(add_candidates(root, urls), 25)
                self.assertEqual(add_candidates(root, urls), 0)
                items = read_queue(root)["items"]
                self.assertEqual(len(items), 25)
                self.assertEqual({item["url"] for item in items}, set(urls))
                self.assertTrue(all(item["state"] == "needs_primary_confirmation"
                                    for item in items))
                self.assertFalse((root / "data/curated_events.json").exists())

    def test_candidate_research_does_not_auto_publish_events(self):
        generated, _ = create_files(ROOT, now_jst())
        self.assertIn("official-events.html", generated)
        guide = generated["official-events.html"]
        self.assertEqual(guide.count('class="card event-source-card"'), 11)
        self.assertIn("個別イベントの掲載は現在準備中", guide)
        self.assertNotIn("さかな文化祭あかし", guide)
        self.assertNotIn("横手の雪まつりin姫路城", guide)
        self.assertNotIn("event-candidate-urls-20261027.txt", guide)
        self.assertIn('content="noindex,follow"', guide)
        self.assertNotIn("<script", guide)


if __name__ == "__main__":
    unittest.main()
