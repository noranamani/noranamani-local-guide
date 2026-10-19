"""No-network coverage of manually curated outing cards and static publication."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from localguide.core import GuideError, parse_time
from localguide.nearby_guides import nearby_cards, nearby_page_body, reviewed_nearby
from localguide.site import create_files

ROOT = Path(__file__).resolve().parents[1]
NOW = parse_time("2026-10-19T18:00:00+09:00")


class NearbyGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "data/nearby_spots.json").read_text(encoding="utf-8"))

    def _validate(self, data):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "data"
            target.mkdir()
            (target / "nearby_spots.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return reviewed_nearby(Path(temporary))

    def test_reviewed_official_only_unique_curated_candidates(self):
        records = reviewed_nearby(ROOT)
        self.assertGreaterEqual(len(records), 9)
        self.assertEqual(len({record["id"] for record in records}), len(records))
        self.assertTrue({'gongen-park', 'mitoro-hill', 'kakurinji-park', 'shikata-east-park'} <= {record['id'] for record in records})
        self.assertTrue(all(record["official_url"].startswith("https://") for record in records))
        self.assertEqual({record["municipality"] for record in records},
                         {"加古川市", "明石市", "播磨町"})
        self.assertEqual(len(self._validate(self.record)), len(records))

    def test_missing_data_is_empty_for_synthetic_workspaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(reviewed_nearby(temporary), [])

    def test_malicious_markup_unapproved_host_and_duplicate_id_stop(self):
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][0]["idea"] = '<script>alert("x")</script>'
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][1]["official_url"] = "https://tracking.example.net/fake"
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][1]["id"] = unsafe["items"][0]["id"]
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["editorial_policy"] = "auto_scrape_all"
        with self.assertRaises(GuideError):
            self._validate(unsafe)

    def test_cards_are_accessible_and_dont_invent_prices_or_visits(self):
        cards = nearby_cards(reviewed_nearby(ROOT))
        self.assertEqual(cards.count('class="card nearby-card"'), len(self.record['items']))
        self.assertEqual(cards.count('rel="noopener noreferrer"'), len(self.record['items']))
        self.assertNotIn("<script", cards)
        self.assertIn("料金・営業時間・年齢条件：施設ごとに公式案内で確認", cards)
        self.assertIn("大中遺跡公園", cards)
        self.assertIn("権現総合公園", cards)
        self.assertIn("みとろの丘", cards)
        self.assertIn("加古川海洋文化センター", cards)
        self.assertIn("公式リンクの最終編集確認日", nearby_page_body(
            reviewed_nearby(ROOT), self.record["reviewed_on"]))

    def test_generated_site_shows_new_guide_without_indexing_or_ad_changes(self):
        files, _ = create_files(ROOT, NOW)
        self.assertIn("nearby.html", files)
        nearby_page = files["nearby.html"]
        home = files["index.html"]
        self.assertIn('content="noindex,follow"', nearby_page)
        self.assertIn('<h1>近場のよりみちガイド</h1>', nearby_page)
        self.assertEqual(nearby_page.count("<h1"), 1)
        self.assertIn('href="nearby.html"', home)
        self.assertIn('id="nearby-guide"', home)
        self.assertIn(f'{len(self.record["items"])}件の候補を見る', home)
        self.assertIn('href="nearby.html" aria-current="page"', nearby_page)
        self.assertLess(home.index('id="family-trip"'), home.index('id="nearby-guide"'))
        self.assertLess(home.index('id="nearby-guide"'), home.index('id="local-spots"'))
        self.assertNotIn("sitemap.xml", files)
        self.assertEqual(files[".guide-manifest.json"].count('"events": 0'), 1)


if __name__ == "__main__":
    unittest.main()
