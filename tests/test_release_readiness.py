"""Offline-only tests for diagnostic release gate."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from localguide.core import parse_time
from localguide.release_readiness import assess, markdown_report

NOW = parse_time("2026-10-15T12:00:00+09:00")


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.index = self.root / "docs/index.html"
        self.headers = self.root / "docs/_headers"
        self.index.write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
        self.headers.write_text("/*\n  X-Robots-Tag: noindex\n", encoding="utf-8")
        self.rules = {"site_url": None, "review": {"stale_event_after_hours": 72},
                      "list_pages": {"min_active_items": 5, "min_official_items": 3,
                                     "min_distinct_organizers": 2},
                      "place_pages": {"min_places": 5, "min_official_places": 3,
                                      "min_distinct_official_hosts": 2}}
        self.data = {"events": {"items": []}, "places": {"items": []}}
        self.registry = {"sources": [{"id": "official_fixture", "enabled": True}]}
        self.manifest = {"files": ["index.html", "_headers"]}
        self.patches = [
            patch("localguide.release_readiness.validate_data", return_value=self.data),
            patch("localguide.release_readiness.validate_config",
                  return_value=({}, {}, self.rules, self.registry)),
            patch("localguide.release_readiness.validate_site", return_value=self.manifest)
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_report_stays_unpublished_and_empty_is_not_success(self):
        state = assess(self.root, NOW)
        self.assertFalse(state["publication_approved"])
        self.assertEqual(state["events"], 0)
        self.assertFalse(state["events_pass"])
        self.assertFalse(state["places_pass"])
        self.assertTrue(state["draft_noindex"])
        report = markdown_report(state)
        self.assertIn("公開判定：保留", report)
        self.assertIn("今後のイベント情報", report)
        self.assertIn("確認済み0件", report)

    def test_manual_reviews_not_marked_done(self):
        state = assess(self.root, NOW)
        report = markdown_report(state)
        self.assertEqual(report.count("- [ ]"), len(state["manual_checks"]))
        self.assertIn("Cloudflare初回デプロイの承認", report)

    def test_missing_xrobots_header_rejected_before_url_set(self):
        self.headers.write_text("/*\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            assess(self.root, NOW)

    def test_invalid_indexable_page_without_url_rejected(self):
        self.index.write_text('<meta name="robots" content="index,follow">', encoding="utf-8")
        with self.assertRaises(ValueError):
            assess(self.root, NOW)

    def test_configured_url_still_does_not_grant_publish_permission(self):
        self.rules["site_url"] = "https://example.org"
        self.index.write_text('<meta name="robots" content="index,follow">', encoding="utf-8")
        self.headers.write_text("/*\n", encoding="utf-8")
        state = assess(self.root, NOW)
        self.assertEqual(state["indexable_pages"], 1)
        self.assertFalse(state["publication_approved"])

    def test_missing_headers_manifest_rejected(self):
        self.manifest["files"] = ["index.html"]
        with self.assertRaises(ValueError):
            assess(self.root, NOW)

    def test_workflow_does_not_contain_cloudflare_deploy(self):
        root = Path(__file__).resolve().parents[1]
        yml = (root / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("python -m scripts.release_readiness", yml)
        self.assertIn("launch-readiness-report.md", yml)
        self.assertNotIn("wrangler pages deploy", yml)
        self.assertNotIn("cloudflare/wrangler-action", yml)


if __name__ == "__main__":
    unittest.main()
