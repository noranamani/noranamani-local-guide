"""Homepage redesign contracts: safe, static, accessible, and grounded in records."""
import unittest
from pathlib import Path
from unittest.mock import patch

from localguide.core import parse_time
from localguide.site import HERO_SCENE, AWAJI_SCENE, STYLE, PHOTO_ASSETS, create_files, page, valid_webp


NOW = parse_time("2026-10-16T13:00:00+09:00")


class HomepageRefreshTests(unittest.TestCase):
    def test_original_artwork_and_responsive_styles(self):
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', HERO_SCENE)
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', AWAJI_SCENE)
        self.assertIn(".home-hero", STYLE)
        self.assertIn(".browse-grid", STYLE)
        self.assertIn("@media (max-width: 600px)", STYLE)
        self.assertNotIn("<image", HERO_SCENE)
        self.assertNotIn("<image", AWAJI_SCENE)

    def test_compact_photo_heroes_keep_legible_titles(self):
        # Avoid the original 500px+ above-the-fold banner, while allowing
        # natural growth when text wraps at narrow widths or zoom levels.
        self.assertIn("min-height: clamp(300px, 28vw, 355px)", STYLE)
        self.assertIn("min-height: 360px", STYLE)
        self.assertIn("min-height: clamp(215px, 23vw, 300px)", STYLE)
        self.assertIn(".article-main .article-cover { min-height: 270px", STYLE)
        self.assertNotIn("min-height: 515px", STYLE)
        self.assertIn('url("harima-hero-photo.webp")', STYLE)
        self.assertIn('url("awaji-photo.webp")', STYLE)

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
            for filename in PHOTO_ASSETS:
                self.assertIn(filename, files)
                self.assertIsInstance(files[filename], bytes)
                self.assertTrue(valid_webp(files[filename]))
                self.assertIn(f'url("{filename}")', files["styles.css"])
            self.assertIn('<h1 id="home-headline">はりまよりみち</h1>', files["index.html"])
            self.assertIn('class="site-header site-header--compact"', files["index.html"])
            self.assertIn('<nav aria-label="主なページ">', files["index.html"])
            self.assertIn('href="index.html" aria-current="page"', files["index.html"])
            self.assertNotIn('class="brand"', files["index.html"])
            self.assertNotIn('class="tagline"', files["index.html"])
            self.assertEqual(files["index.html"].count("<h1"), 1)
            self.assertIn("※画像はイメージです", files["index.html"])
            self.assertNotIn("sitemap.xml", files)


    def test_awaji_article_title_is_real_html_and_only_one_heading(self):
        import json
        from localguide.travel_guides import guide_body
        path = Path(__file__).resolve().parents[1] / "data" / "travel_guides.json"
        guide = next(g for g in json.loads(path.read_text(encoding="utf-8"))["items"]
                     if g["id"] == "awaji-family-one-night")
        body = guide_body(guide)
        document = page(guide["title"], guide["summary"], body,
                        "trip-awaji-family-one-night.html", None, False, "",
                        heading_in_body=True)
        self.assertIn('<div class="article-cover article-cover--awaji"><h1>', document)
        self.assertIn("※画像はイメージです", document)
        self.assertEqual(document.count("<h1"), 1)
        self.assertIn("広告・PR", document)
        self.assertNotIn("<img", document)
        self.assertIn("awaji-photo.webp", STYLE)


if __name__ == "__main__":
    unittest.main()
