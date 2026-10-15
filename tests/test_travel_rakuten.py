"""No-network Rakuten Travel preparation tests; all hotels are fictitious."""
import copy
import unittest

from localguide.core import GuideError
from localguide.travel_rakuten import (api_fetch_ready, normalize_hotel_snapshot,
                                       approve_exact_booking_quote, publication_ready)

NOW = "2026-10-15T12:00:00+09:00"


def settings():
    return {"schema_version": 1, "provider": "rakuten_travel",
            "enabled": False, "affiliate_publication_enabled": False,
            "api_fetch_enabled": False,
            "approvals": {
                "travel_api_access_confirmed": False,
                "local_guide_registered_as_affiliate_site": False,
                "rakuten_webservice_data_terms_reviewed": False,
                "rakuten_official_credit_reviewed": False,
                "hosting_terms_reviewed": False,
            }}


def basic(no=123):
    return {"hotelNo": no, "hotelName": "架空テストホテル",
            "hotelInformationUrl": f"https://travel.rakuten.co.jp/HOTEL/{no}/{no}.html",
            "hotelMinCharge": 3000, "hotelThumbnailUrl": "https://example.org/fiction.png",
            "userReview": "COPYRIGHTED EXAMPLE"}


class RakutenReadinessTests(unittest.TestCase):
    def test_default_disabled(self):
        self.assertFalse(publication_ready(settings(), "https://example.org/travel"))
        self.assertFalse(api_fetch_ready(settings()))

    def test_all_gates_required_for_publication(self):
        s=settings()
        s["enabled"]=s["affiliate_publication_enabled"]=True
        s["api_fetch_enabled"]=True
        s["approvals"]={key: True for key in s["approvals"]}
        self.assertFalse(publication_ready(s))
        self.assertTrue(publication_ready(s, "https://example.org/travel"))
        self.assertTrue(api_fetch_ready(s))
        s["approvals"]["hosting_terms_reviewed"]=False
        self.assertFalse(publication_ready(s, "https://example.org/travel"))

    def test_site_registration_gate(self):
        s=settings()
        s["enabled"]=s["affiliate_publication_enabled"]=True
        s["approvals"]={key: True for key in s["approvals"]}
        s["approvals"]["local_guide_registered_as_affiliate_site"]=False
        self.assertFalse(publication_ready(s, "https://example.org/travel"))

    def test_malformed_review_state_rejected(self):
        s=settings()
        s["approvals"]["travel_api_access_confirmed"]="yes"
        with self.assertRaises(GuideError):
            publication_ready(s, "https://example.org/travel")

    def test_api_fetch_requires_specific_consent(self):
        s=settings()
        s["enabled"]=s["api_fetch_enabled"]=True
        s["approvals"]["travel_api_access_confirmed"]=True
        self.assertFalse(api_fetch_ready(s))
        s["approvals"]["rakuten_webservice_data_terms_reviewed"]=True
        self.assertTrue(api_fetch_ready(s))


class RakutenHotelSnapshotTests(unittest.TestCase):
    def test_wrap_hotel_list_for_review_only(self):
        snap={"hotels":[{"hotel":[{"hotelBasicInfo":basic()},{"hotelRatingInfo":{"foo":1}}]}]}
        result=normalize_hotel_snapshot(snap,NOW)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["hotel_no"],123)
        self.assertIsNone(result[0]["family_total_jpy"])
        self.assertIsNone(result[0]["can_accommodate_party"])
        self.assertFalse(result[0]["publishable"])
        self.assertFalse(result[0]["affiliate_link_verified"])
        self.assertNotIn("hotelMinCharge",str(result))
        self.assertNotIn("COPYRIGHTED EXAMPLE",str(result))

    def test_hotel_basic_dict_wrapper(self):
        snap={"hotels":[{"hotel":{"hotelBasicInfo":basic(124)}}]}
        self.assertEqual(normalize_hotel_snapshot(snap,NOW)[0]["hotel_no"],124)

    def test_hotel_without_list_wrapper(self):
        snap={"hotels":[{"hotelBasicInfo":basic(124)}]}
        self.assertEqual(normalize_hotel_snapshot(snap,NOW)[0]["hotel_no"],124)

    def test_duplicate_ids_rejected(self):
        snap={"hotels":[{"hotelBasicInfo":basic(124)},{"hotelBasicInfo":basic(124)}]}
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot(snap,NOW)

    def test_wrong_domain_rejected(self):
        row=basic()
        row["hotelInformationUrl"]="https://travel.rakuten.co.jp.evil.test/"
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot({"hotels":[{"hotelBasicInfo":row}]},NOW)

    def test_insecure_url_rejected(self):
        row=basic()
        row["hotelInformationUrl"]="http://travel.rakuten.co.jp/example"
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot({"hotels":[{"hotelBasicInfo":row}]},NOW)

    def test_invalid_hotel_id_rejected(self):
        row=basic(True)
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot({"hotels":[{"hotelBasicInfo":row}]},NOW)

    def test_invalid_response_rejected(self):
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot({"hotels":"wrong"},NOW)

    def test_invalid_html_name_rejected(self):
        row=basic()
        row["hotelName"]="<script>oops</script>"
        with self.assertRaises(GuideError):
            normalize_hotel_snapshot({"hotels":[{"hotelBasicInfo":row}]},NOW)


def quote():
    return {
        "checkin_date":"2027-08-01","checkout_date":"2027-08-02","adults":2,
        "children_ages":[16,15,12,9],"rooms":2,"meal_plan":"夕朝食なし",
        "verified_at":NOW,"family_total_jpy":45000,
        "official_plan_url":"https://travel.rakuten.co.jp/"
    }


class FamilyQuoteTests(unittest.TestCase):
    def test_valid_6_person_quote_not_guaranteed(self):
        result=approve_exact_booking_quote(quote())
        self.assertEqual(result["family_total_jpy"],45000)
        self.assertFalse(result["price_is_fixed"])

    def test_reject_missing_child_ages(self):
        q=quote();del q["children_ages"]
        with self.assertRaises(GuideError):
            approve_exact_booking_quote(q)

    def test_reject_partial_occupancy(self):
        q=quote();q["children_ages"]=[]
        with self.assertRaises(GuideError):
            approve_exact_booking_quote(q)

    def test_reject_wrong_date_order(self):
        q=quote();q["checkout_date"]="2027-08-01"
        with self.assertRaises(GuideError):
            approve_exact_booking_quote(q)

    def test_reject_boolean_amount(self):
        q=quote();q["family_total_jpy"]=True
        with self.assertRaises(GuideError):
            approve_exact_booking_quote(q)

    def test_reject_without_meal_condition(self):
        q=quote();q["meal_plan"]=""
        with self.assertRaises(GuideError):
            approve_exact_booking_quote(q)


if __name__=="__main__":
    unittest.main()
