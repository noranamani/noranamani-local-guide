"""Safe, offline coverage for the independent official-event directory."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from localguide.core import GuideError, now_jst
from localguide.official_event_hub import event_finder_body, official_event_links
from localguide.site import create_files

ROOT = Path(__file__).resolve().parents[1]


class OfficialEventHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "data/official_event_links.json").read_text(encoding="utf-8"))

    def validate_copy(self, doc):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            (root / "data/official_event_links.json").write_text(
                json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            return official_event_links(root)

    def test_only_human_reviewed_official_links(self):
        items, reviewed = official_event_links(ROOT)
        self.assertEqual(len(items), 6)
        self.assertEqual(reviewed, "2026-10-27")
        self.assertTrue(all(item["url"].startswith("https://") for item in items))
        self.assertIn("姫路市 イベントカレンダー", {item["name"] for item in items})
        self.assertIn("明石観光協会 イベント一覧", {item["name"] for item in items})
        self.assertEqual(len(self.validate_copy(self.data)[0]), 6)

    def test_duplicate_unreviewed_and_malicious_links_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["policy"] = "scrape_every_day"
        with self.assertRaises(GuideError):
            self.validate_copy(bad)
        bad = copy.deepcopy(self.data)
        bad["items"][1]["id"] = bad["items"][0]["id"]
        with self.assertRaises(GuideError):
            self.validate_copy(bad)
        bad = copy.deepcopy(self.data)
        bad["items"][1]["url"] = "https://unapproved.example/events"
        with self.assertRaises(GuideError):
            self.validate_copy(bad)
        bad = copy.deepcopy(self.data)
        bad["items"][0]["summary"] = "<script>alert(1)</script>"
        with self.assertRaises(GuideError):
            self.validate_copy(bad)

    def test_no_network_no_tracking_and_no_fake_events(self):
        body = event_finder_body(*official_event_links(ROOT))
        self.assertEqual(body.count('class="card event-source-card"'), 6)
        self.assertNotIn("<script", body)
        self.assertNotIn("<img", body)
        self.assertIn("当サイトがイベント日程や空席を自動取得・転載しているわけではありません", body)
        files, _ = create_files(ROOT, now_jst())
        self.assertIn("event-finder.html", files)
        official = files["event-finder.html"]
        self.assertIn('content="noindex,follow"', official)
        self.assertIn('<h1>公式イベント情報を探す</h1>', official)
        self.assertIn('href="event-finder.html" aria-current="page"', official)
        self.assertIn('href="event-finder.html"', files["index.html"])
        self.assertIn('href="about.html"', official)
        self.assertEqual(files[".guide-manifest.json"].count('"events": 0'), 1)
        self.assertNotIn("sitemap.xml", files)
        self.assertNotIn("static.cloudflareinsights.com", official)


if __name__ == "__main__":
    unittest.main()
