"""No-network review and rendered-HTML checks for Himeji official facility links."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from localguide.core import GuideError, now_jst
from localguide.nearby_facility_links import (
    facility_links_section, reviewed_facility_links,
)
from localguide.site import create_files

ROOT = Path(__file__).resolve().parents[1]


class HimejiOfficialFacilityLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            (ROOT / "data/nearby_facility_links.json").read_text(encoding="utf-8")
        )

    def read_fixture(self, data):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data/nearby_facility_links.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return reviewed_facility_links(root)

    def test_reviewed_municipal_links_have_no_remote_collection(self):
        items, reviewed_on = reviewed_facility_links(ROOT)
        self.assertEqual(reviewed_on, "2026-11-16")
        self.assertEqual(len(items), 3)
        self.assertEqual({x["name"] for x in items},
                         {"姫路科学館", "姫路市立水族館", "姫路市立動物園"})
        self.assertTrue(all(x["official_url"].startswith(
            "https://www.city.himeji.lg.jp/") for x in items))
        self.assertEqual(self.read_fixture(self.data)[0], items)

    def test_malformed_unapproved_or_duplicate_record_is_never_rendered(self):
        bad = copy.deepcopy(self.data)
        bad["items"][0]["official_url"] = "https://third-party.example/path"
        with self.assertRaises(GuideError):
            self.read_fixture(bad)
        bad = copy.deepcopy(self.data)
        bad["items"][1]["id"] = bad["items"][0]["id"]
        with self.assertRaises(GuideError):
            self.read_fixture(bad)
        bad = copy.deepcopy(self.data)
        bad["items"][1]["idea"] = "<script>alert(1)</script>"
        with self.assertRaises(GuideError):
            self.read_fixture(bad)
        bad = copy.deepcopy(self.data)
        bad["policy"] = "automatic_html_scraping"
        with self.assertRaises(GuideError):
            self.read_fixture(bad)

    def test_link_only_markup_and_no_unverified_fees(self):
        items, reviewed_on = reviewed_facility_links(ROOT)
        html = facility_links_section(items, reviewed_on)
        self.assertEqual(html.count('class="card event-source-card"'), 3)
        self.assertEqual(html.count('rel="noopener noreferrer"'), 3)
        self.assertNotIn("<img", html)
        self.assertNotIn("<script", html)
        self.assertNotIn("入園無料", html)
        self.assertIn("姫路へ足を延ばす", html)
        self.assertIn("専用駐車場はありません", html)
        self.assertEqual(facility_links_section([], None), "")

    def test_merged_page_keeps_existing_nine_photos_and_reviewed_indexing(self):
        files, _ = create_files(ROOT, now_jst())
        near = files["nearby.html"]
        self.assertIn("姫路科学館", near)
        self.assertIn("姫路市立水族館", near)
        self.assertIn("姫路市立動物園", near)
        self.assertIn('content="index,follow"', near)
        self.assertEqual(near.count('class="card nearby-card"'), 9)
        self.assertEqual(near.count('class="card event-source-card"'), 3)


if __name__ == "__main__":
    unittest.main()
