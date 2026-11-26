"""Selective public-search rollout: only reviewed, useful evergreen pages qualify."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from localguide.core import now_jst, parse_time
from localguide.site import create_files, evergreen_nearby_indexable

ROOT = Path(__file__).resolve().parents[1]
NOW = parse_time("2026-11-19T23:00:00+09:00")
SITE = "https://harima-yorimichi.pages.dev"


class SearchRolloutTests(unittest.TestCase):
    def test_current_canonical_indexable_subset_and_robots(self):
        # This is an integration test against CURRENT committed records, not
        # the 2026-11-19 frozen event fixture used by the test below. The
        # approved CSV updates daily, so a fixed earlier clock becomes invalid.
        files, _ = create_files(ROOT, now_jst())
        wanted = {
            "index.html": SITE + "/",
            "travel-budget.html": SITE + "/travel-budget.html",
        }
        # Reviewed nearby sources can legitimately expire after 60 days.
        # Such a change should mean noindex, not a broken CI build.
        if 'name="robots" content="index,follow"' in files.get("nearby.html", ""):
            wanted["nearby.html"] = SITE + "/nearby.html"
        elif "nearby.html" in files:
            self.assertIn('name="robots" content="noindex,follow"', files["nearby.html"])
            self.assertNotIn('rel="canonical"', files["nearby.html"])
        for filename, canonical in wanted.items():
            with self.subTest(filename=filename):
                page = files[filename]
                self.assertIn('name="robots" content="index,follow"', page)
                self.assertIn(f'rel="canonical" href="{canonical}"', page)
        for filename in ("about.html", "travel.html", "places.html", "official-events.html"):
            if filename in files:
                with self.subTest(noindex=filename):
                    self.assertIn('name="robots" content="noindex,follow"', files[filename])
                    self.assertNotIn('rel="canonical"', files[filename])
        for filename in files:
            if filename.startswith("trip-") and filename.endswith(".html"):
                self.assertIn('name="robots" content="noindex,follow"', files[filename])

        self.assertIn("User-agent: *\nAllow: /\n", files["robots.txt"])
        self.assertIn(SITE + "/sitemap.xml", files["robots.txt"])
        self.assertNotIn("X-Robots-Tag: noindex", files["_headers"])
        sitemap = ET.fromstring(files["sitemap.xml"])
        locations = {item.text for item in sitemap.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
        self.assertTrue(set(wanted.values()) <= locations)
        self.assertNotIn(SITE + "/index.html", locations)
        self.assertNotIn(SITE + "/about.html", locations)
        self.assertNotIn(SITE + "/travel.html", locations)

    def test_nonrecent_or_future_nearby_reviews_not_indexable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data"
            path.mkdir()
            for date, expected in (
                ("2026-09-01", False),
                ("2026-11-20", False),
                ("2026-10-19", True),
            ):
                with self.subTest(date=date):
                    (path / "nearby_spots.json").write_text(json.dumps({"reviewed_on": date}))
                    self.assertEqual(evergreen_nearby_indexable(
                        Path(temp), NOW, [{} for _ in range(6)]), expected)
                    self.assertFalse(evergreen_nearby_indexable(
                        Path(temp), NOW, [{} for _ in range(5)]))


if __name__ == "__main__":
    unittest.main()
