"""Facility listings must never become thin indexable pages (offline only)."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from localguide.core import JST, atomic_json, parse_time
from localguide.page_places import qualified_places, sustained_listing
from localguide.site import create_files


NOW = parse_time("2026-10-14T17:00:00+09:00")
POLICY = {"min_places": 5, "min_official_places": 3, "min_distinct_official_hosts": 2,
          "activate_after_days": 7}


def facility(number, source_id="fixture", primary=True, url=None):
    return {
        "place_id": f"place-{number}", "name": f"架空施設{number}", "municipality": "明石市",
        "address": f"架空所在地{number}", "admission": None, "indoor_outdoor": "unknown",
        "official_url": url or f"https://example{number % 3}.org/place/{number}",
        "sources": [{
            "source_id": source_id,
            "url": "https://example.org/datasets/official.csv",
            "source_event_id": str(number),
            "fetched_at": NOW.isoformat(),
            "last_checked_at": NOW.isoformat(),
            "source_published_at": "2026-08-25",
            "is_primary": primary
        }],
        "last_verified_at": NOW.isoformat()
    }


class PlaceListingUnitTests(unittest.TestCase):
    def test_four_never_qualify(self):
        self.assertFalse(qualified_places([facility(i) for i in range(4)], POLICY))

    def test_five_diverse_official_places_qualify(self):
        self.assertTrue(qualified_places([facility(i) for i in range(5)], POLICY))

    def test_duplicate_official_urls_do_not_qualify(self):
        self.assertFalse(qualified_places([
            facility(i, url="https://example.org/the-same-page") for i in range(5)
        ], POLICY))

    def test_one_host_is_insufficient(self):
        self.assertFalse(qualified_places([
            facility(i, url=f"https://example.org/place/{i}") for i in range(5)
        ], POLICY))

    def test_less_than_three_primary_records_is_insufficient(self):
        self.assertFalse(qualified_places([
            facility(i, primary=i < 2) for i in range(5)
        ], POLICY))

    def test_duplicate_place_id_disqualifies(self):
        data = [facility(i) for i in range(5)]
        data[4]["place_id"] = data[0]["place_id"]
        self.assertFalse(qualified_places(data, POLICY))

    def test_history_requires_week_with_no_gaps(self):
        state = {}
        self.assertFalse(sustained_listing("places.html", True, state, NOW, 7))
        self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=1), 7))
        self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=5), 7))
        self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=6), 7))
        self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=12), 7))
        for day in range(13, 19):
            self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=day), 7))
        self.assertTrue(sustained_listing("places.html", True, state, NOW + timedelta(days=19), 7))

    def test_history_resets_when_quality_drops(self):
        state = {}
        sustained_listing("places.html", True, state, NOW, 7)
        self.assertFalse(sustained_listing("places.html", False, state, NOW + timedelta(days=7), 7))
        self.assertNotIn("places.html", state)

    def test_history_resets_on_clock_reversal(self):
        state = {}
        sustained_listing("places.html", True, state, NOW, 7)
        later = NOW + timedelta(days=3)
        sustained_listing("places.html", True, state, later, 7)
        self.assertFalse(sustained_listing("places.html", True, state, NOW + timedelta(days=1), 7))


class PlaceListingSiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = NOW
        self.places = [facility(i) for i in range(4)]
        self.rules = {
            "site_url": "https://example.org/local-guide",
            "place_pages": POLICY,
            "review": {"stale_event_after_hours": 72},
            "list_pages": {"min_active_items": 5, "min_official_items": 3,
                           "min_distinct_organizers": 2, "activate_after_days": 7}
        }
        self.config = {
            "sources": [{"id": "fixture", "label": "テスト用公式施設CSV",
                         "permission_document": "https://example.org/license",
                         "attribution_url": "https://example.org/data",
                         "adaptation_notice": "架空の事実データを整理して表示"}]
        }

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, now=None):
        self.now = now or self.now
        data = {"events": {"items": []}, "places": {"items": self.places}}
        areas = {"areas": [{"id": "akashi", "name": "明石市"}]}
        cats = {"primary": [{"id": "event", "label": "イベント"}]}
        with patch("localguide.site.validate_data", return_value=data), (
                patch("localguide.site.validate_config",
                      return_value=(areas, cats, self.rules, self.config))), (
                patch("localguide.site.publishable", return_value=True)):
            files, state = create_files(self.root, self.now)
        (self.root / "cache").mkdir(exist_ok=True)
        atomic_json(self.root / "cache/page_state.json", state)
        return files

    def test_four_places_render_but_stay_noindex(self):
        files = self.render()
        self.assertIn("places.html", files)
        self.assertIn("架空施設0", files["places.html"])
        self.assertIn('href="places.html"', files["index.html"])
        self.assertIn('content="noindex,follow"', files["index.html"])
        self.assertIn('content="noindex,follow"', files["places.html"])
        self.assertNotIn("sitemap.xml", files)

    def test_only_five_places_after_week_become_indexable(self):
        self.places = [facility(i) for i in range(5)]
        files = self.render()
        self.assertNotIn("sitemap.xml", files)
        for day in range(1, 8):
            files = self.render(NOW + timedelta(days=day))
        self.assertIn('content="index,follow"', files["places.html"])
        self.assertIn('content="index,follow"', files["index.html"])
        self.assertIn("/places.html", files["sitemap.xml"])
        self.assertIn("/index.html", files["sitemap.xml"])

    def test_site_url_required_even_after_week(self):
        self.rules["site_url"] = None
        self.places = [facility(i) for i in range(5)]
        self.render()
        for day in range(1, 8):
            files = self.render(NOW + timedelta(days=day))
        self.assertIn('content="noindex,follow"', files["index.html"])
        self.assertIn('content="noindex,follow"', files["places.html"])
        self.assertNotIn("sitemap.xml", files)

    def test_reduced_places_remove_listings_from_sitemap(self):
        self.places = [facility(i) for i in range(5)]
        self.render()
        for day in range(1, 8):
            self.render(NOW + timedelta(days=day))
        self.places = [facility(i) for i in range(3)]
        files = self.render(NOW + timedelta(days=8))
        self.assertNotIn("sitemap.xml", files)
        self.assertIn('content="noindex,follow"', files["places.html"])

    def test_zero_places_has_no_empty_places_page(self):
        self.places = []
        files = self.render()
        self.assertNotIn("places.html", files)
        self.assertIn("掲載準備中", files["index.html"])


if __name__ == "__main__":
    unittest.main()
