"""Offline preview report tests. Never use the network or external credentials."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.preview_report import markdown_report, preview_status


class PreviewReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for folder in ("docs", "config"):
            (self.root / folder).mkdir()
        (self.root / "docs/index.html").write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
        (self.root / "docs/places.html").write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
        self.put("docs/.guide-manifest.json", {
            "generated_at": "2026-10-14T18:00:00+09:00",
            "schema_version": 1,
            "files": ["index.html", "places.html", "styles.css"], "events": 0, "places": 4
        })
        self.put("config/sources.json", {"sources": [{"enabled": True}, {"enabled": False}]})
        self.put("config/page_rules.json", {"site_url": None})

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, data):
        (self.root / name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_non_indexable_preview(self):
        state = preview_status(self.root)
        self.assertEqual(state["events"], 0)
        self.assertEqual(state["places"], 4)
        self.assertEqual(state["html_total"], 2)
        self.assertEqual(state["html_noindex"], 2)
        self.assertEqual(state["sources_enabled"], 1)
        self.assertFalse(state["sitemap"])

    def test_report_not_claimed_published(self):
        text = markdown_report(preview_status(self.root))
        self.assertIn("未公開プレビュー", text)
        self.assertIn("0件", text)
        self.assertIn("noindex", text)

    def test_wrong_robots_directive_rejected(self):
        (self.root / "docs/places.html").write_text('<meta name="robots" content="nofollow">', encoding="utf-8")
        with self.assertRaises(ValueError):
            preview_status(self.root)

    def test_indexable_page_without_site_url_rejected(self):
        (self.root / "docs/index.html").write_text('<meta name="robots" content="index,follow">', encoding="utf-8")
        with self.assertRaises(ValueError):
            preview_status(self.root)

    def test_indexable_page_with_valid_url_allowed(self):
        self.put("config/page_rules.json", {"site_url": "https://example.org/local-guide"})
        (self.root / "docs/index.html").write_text('<meta name="robots" content="index,follow">', encoding="utf-8")
        self.assertEqual(preview_status(self.root)["html_indexable"], 1)


if __name__ == "__main__":
    unittest.main()
