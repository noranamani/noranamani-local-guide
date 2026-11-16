"""Offline contract for the complete Cloudflare delivery smoke."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.live_site_probe import (
    BASE, PAGES, MAX_ATTEMPTS, RETRY_SECONDS, check, evaluate, inventory, local_reference_errors, url_path,
)


class LiveSiteSmokeTests(unittest.TestCase):
    def page(self, route):
        return ('<html><head><title>はりまよりみち</title>'
                '<meta name="robots" content="noindex,follow"></head><body>'
                + " ".join(PAGES.get(route, ())) + '</body></html>')

    def test_cloudflare_deploy_delay_window_is_several_minutes(self):
        self.assertGreaterEqual((MAX_ATTEMPTS - 1) * RETRY_SECONDS, 180)
        self.assertLess((MAX_ATTEMPTS - 1) * RETRY_SECONDS, 420)

    def test_existing_five_page_rules_and_noindex(self):
        for route in PAGES:
            with self.subTest(route=route):
                self.assertEqual(evaluate(route, self.page(route), {}), [])
        self.assertTrue(evaluate("/travel.html",
                                 self.page("/travel.html").replace(
                                     "noindex,follow", "index,follow"), {}))
        self.assertTrue(evaluate("/travel.html",
                                 self.page("/travel.html").replace(
                                     "trip-himeji-ako-family-one-night.html", ""), {}))
        self.assertTrue(evaluate("/", self.page("/"), {"X-Robots-Tag": "index,follow"}))
        self.assertEqual(evaluate("/", self.page("/"), {"X-Robots-Tag": "noindex"}), [])
        self.assertEqual(BASE, "https://harima-yorimichi.pages.dev")

    def test_manifest_identifies_all_public_assets_and_rejects_invalid_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t) / "docs"
            docs.mkdir()
            names = ["index.html", "styles.css", "official-events.html",
                     "travel.html", "nearby.html", "places.html",
                     "nearby-hero.webp", "_headers"]
            for name in names:
                (docs / name).write_text("fixture", encoding="utf-8")
            manifest = docs / ".guide-manifest.json"
            manifest.write_text(json.dumps({"files": names}), encoding="utf-8")
            self.assertEqual(len(inventory(t)), len(names) - 1)
            manifest.write_text(json.dumps({"files": names + ["index.html"]}))
            with self.assertRaises(ValueError):
                inventory(t)
            manifest.write_text(json.dumps({"files": ["index.html", "styles.css"]}))
            with self.assertRaises(ValueError):
                inventory(t)

    def test_internal_links_checked_without_fetching_any_external_domains(self):
        html = ('<a href="nearby.html#gongen-park">nearby</a>'
                '<link href="styles.css" rel="stylesheet">'
                '<img src="nearby-hero.webp">'
                '<a href="https://www.city.kakogawa.lg.jp/events">city</a>'
                '<img src="https://hbb.afl.rakuten.co.jp/hgb/sample">ad</a>')
        expected = {"index.html", "nearby.html", "styles.css", "nearby-hero.webp"}
        self.assertEqual(local_reference_errors("/", html, expected), [])
        self.assertTrue(local_reference_errors(
            "/", html.replace("nearby-hero.webp", "lost.webp"), expected))

    def test_response_content_types_and_byte_checks(self):
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t) / "docs"
            docs.mkdir()
            css = b"body { color: black; }"
            html = self.page("/").encode()
            (docs / "index.html").write_bytes(html)
            (docs / "styles.css").write_bytes(css)
            expected = {"index.html", "styles.css"}
            def ok(path):
                return (html, {"Content-Type": "text/html"}) if path == "/" else (
                    css, {"Content-Type": "text/css"})
            self.assertEqual(check("index.html", t, expected, ok), [])
            self.assertEqual(check("styles.css", t, expected, ok), [])
            self.assertTrue(check("styles.css", t, expected,
                                  lambda _: (b"changed", {"Content-Type": "text/css"})))
            self.assertTrue(check("index.html", t, expected,
                                  lambda _: (html, {"Content-Type": "text/plain"})))
        self.assertEqual(url_path("index.html"), "/")


if __name__ == "__main__":
    unittest.main()
