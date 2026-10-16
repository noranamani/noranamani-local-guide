"""Public branding must not expose the GitHub account handle."""
import json
import unittest
from pathlib import Path

from localguide.site import SITE_NAME, SITE_TAGLINE, page

ROOT = Path(__file__).resolve().parents[1]


class PublicBrandingTests(unittest.TestCase):
    def test_site_name_and_tagline(self):
        self.assertEqual(SITE_NAME, "はりまよりみち")
        self.assertIn("加古川", SITE_TAGLINE)
        self.assertIn("明石", SITE_TAGLINE)
        self.assertIn("姫路", SITE_TAGLINE)
        self.assertNotIn("noranamani", SITE_NAME.lower())

    def test_html_title_and_header_use_public_name(self):
        html = page("おでかけ情報", "説明文", "<p>本文</p>", "index.html",
                    None, False, '<a href="index.html">ホーム</a>')
        self.assertIn("<title>おでかけ情報 | はりまよりみち</title>", html)
        self.assertIn('href="index.html">はりまよりみち</a>', html)
        self.assertIn(SITE_TAGLINE, html)
        self.assertNotIn("noranamani", html)

    def test_accessible_mobile_layout_and_draft_guidance(self):
        from localguide.site import STYLE, create_files
        from localguide.core import parse_time
        from unittest.mock import patch
        from tempfile import TemporaryDirectory
        self.assertIn("@media (max-width: 600px)", STYLE)
        self.assertIn("prefers-reduced-motion", STYLE)
        rendered = page("案内", "説明", "<p>本文</p>", "index.html", None, False, "")
        self.assertIn('href="#main-content"', rendered)
        self.assertIn('id="main-content"', rendered)
        self.assertIn('content="noindex,follow"', rendered)
        self.assertNotIn('rel="canonical"', rendered)
        with TemporaryDirectory() as temp:
            root = Path(temp)
            data = {"events": {"items": []}, "places": {"items": []}}
            rules = {"site_url": None, "review": {"stale_event_after_hours": 72},
                     "list_pages": {"min_active_items": 5, "min_official_items": 3,
                                    "min_distinct_organizers": 2, "activate_after_days": 7},
                     "place_pages": {"min_places": 5, "min_official_places": 3,
                                      "min_distinct_official_hosts": 2, "activate_after_days": 7}}
            config = {"sources": []}
            with patch("localguide.site.validate_data", return_value=data), patch(
                "localguide.site.validate_config",
                return_value=({"areas": []}, {"primary": []}, rules, config)
            ):
                files, _ = create_files(root, parse_time("2026-10-16T10:00:00+09:00"))
            self.assertIn("掲載準備中", files["index.html"])
            self.assertIn("播磨のおでかけを", files["index.html"])
            self.assertIn("X-Robots-Tag: noindex", files["_headers"])

    def test_attribution_in_source_config_has_public_brand(self):
        config = json.loads((ROOT / "config/sources.json").read_text(encoding="utf-8"))
        official = next(s for s in config["sources"] if s["id"] == "akashi_open_data")
        notice = official["adaptation_notice"]
        self.assertIn("はりまよりみち", notice)
        self.assertNotIn("noranamani", notice)

    def test_committed_static_preview_uses_public_brand(self):
        html = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn("はりまよりみち", html)
        self.assertNotIn("noranamani", html)

    def test_previews_use_public_name(self):
        preview = (ROOT / "scripts/preview_report.py").read_text(encoding="utf-8")
        release = (ROOT / "localguide/release_readiness.py").read_text(encoding="utf-8")
        self.assertIn("はりまよりみち", preview)
        self.assertIn("はりまよりみち", release)


if __name__ == "__main__":
    unittest.main()
