"""Layout navigation contracts: one visible heading and accessible, linked cards."""
import json
import unittest
from pathlib import Path

from localguide.site import STYLE, page
from localguide.travel_guides import guide_body, guide_card

ROOT = Path(__file__).resolve().parents[1]


class LayoutPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guides = json.loads(
            (ROOT / "data/travel_guides.json").read_text(encoding="utf-8")
        )["items"]

    def test_home_nav_is_compact_and_has_active_state_without_second_brand(self):
        doc = page("家族で出かける地域ガイド", "地域情報を見る",
                   '<section class="home-hero"><h1>はりまよりみち</h1></section>',
                   "index.html", None, False,
                   '<a href="index.html">ホーム</a><a href="travel.html">家族旅行</a>',
                   home=True)
        self.assertEqual(doc.count("<h1"), 1)
        self.assertIn('<header class="site-header site-header--compact">', doc)
        self.assertNotIn('class="brand"', doc)
        self.assertNotIn('class="tagline"', doc)
        self.assertIn('href="index.html" aria-current="page"', doc)
        self.assertIn('aria-label="フッターの案内"', doc)

    def test_article_nav_and_day_jump_targets(self):
        for guide in self.guides:
            with self.subTest(guide=guide["id"]):
                body = guide_body(guide)
                filename = "trip-" + guide["id"] + ".html"
                doc = page(guide["title"], guide["summary"], body,
                           filename, None, False,
                           '<a href="index.html">ホーム</a>'
                           '<a href="travel.html">家族旅行</a>',
                           heading_in_body=True)
                self.assertIn('class="breadcrumbs"', doc)
                self.assertIn('href="travel.html" aria-current="page"', doc)
                self.assertEqual(doc.count("<h1"), 1)
                self.assertEqual(doc.count('class="route-day"'), len(guide["days"]))
                self.assertEqual(doc.count('class="route-step"'),
                                 sum(len(day["stops"]) for day in guide["days"]))
                for day_num in range(1, len(guide["days"]) + 1):
                    self.assertIn(f'href="#day-{day_num}"', doc)
                    self.assertIn(f'id="day-{day_num}"', doc)
                self.assertIn('href="travel.html">← 家族旅行の一覧に戻る', doc)

    def test_full_travel_card_is_one_link_with_clear_call_to_action(self):
        for guide in self.guides:
            with self.subTest(guide=guide["id"]):
                card = guide_card(guide)
                self.assertEqual(card.count("<a "), 1)
                self.assertEqual(card.count("</a>"), 1)
                self.assertIn('class="trip-card__link"', card)
                self.assertIn('プランを読む →', card)
                self.assertIn(guide["summary"], card)

    def test_featured_cards_are_short_with_accessible_full_titles(self):
        for guide in self.guides:
            with self.subTest(guide=guide["id"]):
                compact = guide_card(guide, compact=True)
                full = guide_card(guide)
                self.assertIn('class="card trip-card trip-card--compact"', compact)
                self.assertIn('aria-label="' + guide["title"] + 'を読む"', compact)
                self.assertIn("広告・PRリンクあり", compact)
                self.assertIn("広告・PRリンク", full)
                self.assertIn(guide["summary"], full)
                self.assertEqual(compact.count("<a "), 1)
                self.assertNotIn("<img", compact)
        awaji = next(g for g in self.guides if g["id"] == "awaji-family-one-night")
        sanin = next(g for g in self.guides if g["id"] == "sanin-family-one-night")
        self.assertIn("<h3>淡路島1泊2日</h3>", guide_card(awaji, compact=True))
        self.assertIn("モデルコース", guide_card(awaji, compact=True))
        self.assertIn("<h3>山陰1泊2日</h3>", guide_card(sanin, compact=True))
        self.assertIn("実際の旅行記", guide_card(sanin, compact=True))

    def test_mobile_travel_grid_is_compact_and_keyboard_accessible(self):
        self.assertIn(".home-trip-cards { grid-template-columns: repeat(2, minmax(0, 1fr))", STYLE)
        self.assertIn("@media (max-width: 340px)", STYLE)
        self.assertIn(".trip-card__visual-label", STYLE)
        self.assertIn(".trip-card--compact .trip-card__summary", STYLE)
        self.assertIn(".trip-card__link:focus-visible", STYLE)

    def test_css_has_responsive_and_keyboard_accessible_navigation(self):
        for required in ('.site-header nav a[aria-current="page"]',
                         '.trip-card__link:focus-visible', '.article-jump',
                         '.route-step__pin', '.place-card__official',
                         '@media (max-width: 600px)',
                         '@media (prefers-reduced-motion: reduce)'):
            self.assertIn(required, STYLE)


if __name__ == "__main__":
    unittest.main()
