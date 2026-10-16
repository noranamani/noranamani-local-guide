"""Offline tests: visible editorial drafts never create affiliate ads or invented prices."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from localguide.core import GuideError, parse_time
from localguide.travel_guides import (reviewed_guides, guide_body,
                                      guide_card, travel_filename, search_eligible,
                                      approved_affiliate_html)

ROOT = Path(__file__).resolve().parents[1]
NOW = parse_time("2026-10-16T11:00:00+09:00")


class FamilyTravelEditorialTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "data/travel_guides.json").read_text(encoding="utf-8"))
        self.guide = self.data["items"][0]

    def test_schema_and_distinct_primary_links(self):
        schema = json.loads((ROOT / "schemas/travel_guides.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(self.data)
        guides = reviewed_guides(self.data, NOW)
        self.assertEqual(len(guides), 2)
        self.assertEqual(guides[0]["review_status"], "preview")
        urls = [stop["official_url"] for day in self.guide["days"] for stop in day["stops"]]
        self.assertEqual(len(set(urls)), 3)

    def test_preview_content_has_unmodified_rakuten_link_with_prominent_pr_notice(self):
        self.assertEqual(travel_filename(self.guide), "trip-awaji-family-one-night.html")
        self.assertFalse(search_eligible(self.guide, NOW))
        original = self.guide["affiliate"]["source_html"]
        content = guide_body(self.guide)
        self.assertIn("イングランドの丘", content)
        self.assertIn("あわじ花さじき", content)
        self.assertIn("国営明石海峡公園", content)
        self.assertIn('href="https://www.england-hill.com/"', content)
        self.assertEqual(approved_affiliate_html(self.guide), original)
        self.assertEqual(content.count(original), 1)
        self.assertIn('target="_blank" rel="nofollow sponsored noopener"', content)
        self.assertIn('style="word-wrap:break-word;"', content)
        self.assertIn("広告・PR", content)
        self.assertLess(content.index("広告・PR：この記事には"), content.index("2日間の回り方案"))
        self.assertIn("家族4〜6人", content)
        self.assertIn("淡路島エリア宿泊施設一覧", content)
        self.assertIn("記事確認中", guide_card(self.guide))
        self.assertIn("広告・PRリンク", guide_card(self.guide))
        self.assertIn('class="travel-booking-reference"', content)
        self.assertNotIn('class="affiliate-link"', content)
        destination = self.guide["affiliate"]["destination_url"]
        self.assertEqual(content.count(f'href="{destination}"'), 1)
        self.assertIn('楽天トラベルの淡路島エリア宿泊施設一覧（通常リンク）', content)
        self.assertIn("この通常リンクにはアフィリエイト報酬は発生しません", content)
        # Visitors whose ad blocker hides affiliate markup can still open the official listing.
        self.assertGreater(content.index(f'href="{destination}"'), content.index(original))
        from localguide.site import STYLE
        self.assertIn(".travel-booking-reference", STYLE)
        self.assertNotIn(".affiliate-link", STYLE)

    def test_disabling_link_falls_back_to_preparation_only(self):
        guide = copy.deepcopy(self.guide)
        guide.pop("affiliate")
        guide["lodging_note"] = "宿泊候補と人数条件を整理しています。広告・予約リンクは未掲載です。"
        content = guide_body(guide)
        self.assertNotIn("hb.afl.rakuten.co.jp", content)
        self.assertIn("楽天トラベル広告は準備中", content)
        self.assertNotIn("広告・PR：この記事には", content)
        self.assertIn("広告リンクは準備中", guide_card(guide))
        self.assertNotIn("通常リンク", content)
        self.assertNotIn("travel-booking-reference", content)

    def test_manual_link_rejects_rewritten_markup_and_bad_registration(self):
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["source_html"] = unsafe["affiliate"]["source_html"].replace(
            'target="_blank"', 'target="_self"')
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["source_html"] += "<script>alert(1)</script>"
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["site_registered"] = False
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["registered_site_url"] = "https://unregistered.example.net/"
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)

    def test_manual_link_rejects_mismatched_destination_and_tracking(self):
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["destination_url"] = "https://travel.rakuten.co.jp/yado/other.html"
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["source_html"] = unsafe["affiliate"]["source_html"].replace(
            "hb.afl.rakuten.co.jp", "evil.example.net")
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)
        unsafe = copy.deepcopy(self.guide)
        unsafe["affiliate"]["source_html"] = unsafe["affiliate"]["source_html"].replace(
            "link_type=text", "link_type=image")
        with self.assertRaises(GuideError):
            approved_affiliate_html(unsafe)

    def test_sanin_actual_trip_route_and_original_picttext_ad(self):
        sanin = next(g for g in self.data["items"] if g["id"] == "sanin-family-one-night")
        self.assertEqual(sanin["trip_basis"], "actual_trip")
        self.assertEqual(sanin["review_status"], "preview")
        self.assertFalse(search_eligible(sanin, NOW))
        names = [stop["name"] for day in sanin["days"] for stop in day["stops"]]
        self.assertEqual(names, [
            "水木しげるロード", "松江市宍道ふるさと森林公園（立ち寄り）",
            "出雲大社・出雲方面の観光", "松江市宍道ふるさと森林公園（宿泊）",
            "青山剛昌ふるさと館", "鳥取砂丘"])
        original = sanin["affiliate"]["source_html"]
        self.assertEqual(approved_affiliate_html(sanin), original)
        content = guide_body(sanin)
        self.assertEqual(content.count(original), 1)
        self.assertIn('<h1>' + sanin["title"] + '</h1>', content)
        self.assertIn('class="travel-booking-reference travel-booking-reference--picttext"', content)
        self.assertLess(content.index("広告・PR：この記事には"), content.index("1泊2日の訪問ルート"))
        self.assertIn("2026年の家族旅行", content)
        self.assertIn("旅行記（記事確認中）", guide_card(sanin))

    def test_sanin_picttext_ad_rejects_rewrites_and_cross_property_tracking(self):
        sanin = next(g for g in self.data["items"] if g["id"] == "sanin-family-one-night")
        changes = [
            ("target=\"_blank\"", "target=\"_self\""),
            ('item_id=84942', 'item_id=11111'),
            ('img.travel.rakuten.co.jp', 'evil.example.com'),
            ("link_type=picttext", "link_type=text"),
            ("松江市宍道ふるさと森林公園</a>", "不正な宿泊先</a>"),
        ]
        for original, replacement in changes:
            with self.subTest(original=original):
                changed = copy.deepcopy(sanin)
                changed["affiliate"]["source_html"] = sanin["affiliate"]["source_html"].replace(
                    original, replacement)
                self.assertNotEqual(changed["affiliate"]["source_html"],
                                    sanin["affiliate"]["source_html"])
                with self.assertRaises(GuideError):
                    approved_affiliate_html(changed)
        appended = copy.deepcopy(sanin)
        appended["affiliate"]["source_html"] += '<script>alert(1)</script>'
        with self.assertRaises(GuideError):
            approved_affiliate_html(appended)

    def test_historical_build_cannot_show_future_review(self):
        old = parse_time("2026-10-14T10:00:00+09:00")
        self.assertEqual(reviewed_guides(self.data, old), [])

    def test_approval_requires_current_source_review(self):
        approved = copy.deepcopy(self.guide)
        approved["review_status"] = "approved"
        self.assertTrue(search_eligible(approved, NOW))
        self.assertFalse(search_eligible(approved, NOW + timedelta(days=91)))
        self.assertFalse(search_eligible(self.guide, NOW))

    def test_refuse_insecure_and_duplicate_sources(self):
        malformed = copy.deepcopy(self.data)
        malformed["items"][0]["days"][0]["stops"][0]["official_url"] = "http://example.com/"
        with self.assertRaises(GuideError):
            reviewed_guides(malformed, NOW)
        duplicated = copy.deepcopy(self.data)
        duplicated["items"].append(copy.deepcopy(duplicated["items"][0]))
        with self.assertRaises(GuideError):
            reviewed_guides(duplicated, NOW)

    def test_approved_not_auto_from_rakuten_setting(self):
        affiliate = json.loads((ROOT / "config/travel_affiliate.json").read_text(encoding="utf-8"))
        self.assertFalse(affiliate["enabled"])
        self.assertFalse(affiliate["affiliate_publication_enabled"])
        self.assertTrue(affiliate["approvals"]["local_guide_registered_as_affiliate_site"])
        self.assertFalse(any(value for key, value in affiliate["approvals"].items()
                             if key != "local_guide_registered_as_affiliate_site"))


if __name__ == "__main__":
    unittest.main()
