"""Homepage redesign contracts: safe, static, accessible, and grounded in records."""
import unittest
from pathlib import Path
from unittest.mock import patch

from localguide.core import parse_time
from localguide.site import HERO_SCENE, AWAJI_SCENE, STYLE, create_files


NOW = parse_time("2026-10-16T13:00:00+09:00")


class HomepageRefreshTests(unittest.TestCase):
    def test_original_artwork_and_responsive_styles(self):
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', HERO_SCENE)
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', AWAJI_SCENE)
        self.assertIn(".home-hero", STYLE)
        self.assertIn(".browse-grid", STYLE)
        self.assertIn("@media (max-width: 600px)", STYLE)
        self.assertNotIn("https://", HERO_SCENE)
        self.assertNotIn("https://", AWAJI_SCENE)

    def test_empty_home_does_not_invent_events_or_links(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rules = {"site_url": None,
                     "review": {"stale_event_after_hours": 72},
                     "list_pages": {"min_active_items": 5, "min_official_items": 3,
                                    "min_distinct_organizers": 2, "activate_after_days": 7},
                     "place_pages": {"min_places": 5, "min_official_places": 3,
                                     "min_distinct_official_hosts": 2, "activate_after_days": 7}}
            with patch("localguide.site.validate_data", return_value={
                "events": {"items": []},
                "places": {"items": []},
                "travel_guides": {"schema_version": 1, "items": []}
            }), patch("localguide.site.validate_config", return_value=(
                {"areas": []}, {"primary": []}, rules, {"sources": []}
            )):
                files, _ = create_files(root, NOW)
            self.assertIn("週末、ちょっと", files["index.html"])
            self.assertIn("掲載準備中", files["index.html"])
            self.assertIn("イベント情報は準備中", files["index.html"])
            self.assertNotIn('href="travel.html"', files["index.html"])
            self.assertNotIn('href="places.html"', files["index.html"])
            self.assertIn('content="noindex,follow"', files["index.html"])
            self.assertIn('X-Robots-Tag: noindex', files["_headers"])
            self.assertIn("harima-hero.svg", files)
            self.assertIn("awaji-card.svg", files)
            self.assertNotIn("sitemap.xml", files)


if __name__ == "__main__":
    unittest.main()
