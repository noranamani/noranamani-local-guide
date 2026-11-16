"""Offline validation of the published-site read-only probe."""
import unittest

from scripts.live_site_probe import BASE, PAGES, evaluate


class LiveSiteSmokeTests(unittest.TestCase):
    def page(self, path):
        return ('<html><head><title>はりまよりみち</title>'
                '<meta name="robots" content="noindex,follow"></head><body>'
                + " ".join(PAGES[path]) + '</body></html>')

    def test_required_content_passes_without_network(self):
        for path in PAGES:
            with self.subTest(path=path):
                self.assertEqual(evaluate(path, self.page(path), {}), [])

    def test_removed_content_or_noindex_is_reported(self):
        page = self.page("/travel.html")
        self.assertTrue(evaluate("/travel.html", page.replace("noindex,follow", "index,follow"), {}))
        self.assertTrue(evaluate("/travel.html",
                                 page.replace("trip-himeji-ako-family-one-night.html", ""), {}))

    def test_conflicting_robots_header_is_reported(self):
        self.assertTrue(evaluate("/", self.page("/"), {"X-Robots-Tag": "index,follow"}))
        self.assertEqual(evaluate("/", self.page("/"), {"X-Robots-Tag": "noindex"}), [])

    def test_base_is_explicit_owned_https_host(self):
        self.assertEqual(BASE, "https://harima-yorimichi.pages.dev")


if __name__ == "__main__":
    unittest.main()
