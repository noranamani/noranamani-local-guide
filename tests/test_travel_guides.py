"""Offline tests: visible editorial drafts never create affiliate ads or invented prices."""
import copy
import json
import unittest
from datetime import timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from localguide.core import GuideError, parse_time
from localguide.travel_guides import (reviewed_guides, guide_body,
                                      guide_card, travel_filename, search_eligible)

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
        self.assertEqual(len(guides), 1)
        self.assertEqual(guides[0]["review_status"], "preview")
        urls = [stop["official_url"] for day in self.guide["days"] for stop in day["stops"]]
        self.assertEqual(len(set(urls)), 3)

    def test_preview_content_is_genuinely_useful_without_ads(self):
        self.assertEqual(travel_filename(self.guide), "trip-awaji-family-one-night.html")
        self.assertFalse(search_eligible(self.guide, NOW))
        content = guide_body(self.guide)
        self.assertIn("イングランドの丘", content)
        self.assertIn("あわじ花さじき", content)
        self.assertIn("国営明石海峡公園", content)
        self.assertIn("楽天トラベル広告は準備中", content)
        self.assertNotIn("hb.afl.rakuten.co.jp", content)
        self.assertNotIn("afl.rakuten.co.jp", content)
        self.assertIn("宿泊施設の紹介", content)
        self.assertIn('href="https://www.england-hill.com/"', content)
        self.assertIn("記事確認中", guide_card(self.guide))

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
        self.assertFalse(any(affiliate["approvals"].values()))


if __name__ == "__main__":
    unittest.main()
