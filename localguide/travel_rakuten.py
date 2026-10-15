"""Offline preparations for Rakuten Travel; no HTTP, token access or publishing.

The 2026-07-31 hotel APIs return hotelBasicInfo with hotelNo,
hotelName, hotelInformationUrl and hotelMinCharge. The last field is a
ONE-ROOM, ONE-NIGHT starting indication, never a price for 4-6 guests.
"""
from urllib.parse import urlsplit

from .core import GuideError, parse_time, safe_url

MAX_HOTELS = 30
REQUIRED_APPROVALS = (
    "travel_api_access_confirmed",
    "local_guide_registered_as_affiliate_site",
    "rakuten_webservice_data_terms_reviewed",
    "rakuten_official_credit_reviewed",
    "hosting_terms_reviewed",
)
HOTEL_FIELDS = ("hotelNo", "hotelName", "hotelInformationUrl")


def publication_ready(config, site_url=None):
    """Unpublished until all independent registrations and reviews are done."""
    if config.get("schema_version") != 1 or config.get("provider") != "rakuten_travel":
        raise GuideError("楽天トラベル設定の版または提供元が不正です")
    approvals = config.get("approvals")
    if not isinstance(approvals, dict):
        raise GuideError("アフィリエイト承認設定が不正です")
    if any(not isinstance(approvals.get(key), bool) for key in REQUIRED_APPROVALS):
        raise GuideError("利用条件の承認項目が不正です")
    if not config.get("enabled") or not config.get("affiliate_publication_enabled"):
        return False
    if not all(approvals[key] for key in REQUIRED_APPROVALS):
        return False
    if not site_url:
        return False
    safe_url(site_url)
    return True


def api_fetch_ready(config):
    """Application credentials are never in this config or committed to Git."""
    if config.get("schema_version") != 1 or config.get("provider") != "rakuten_travel":
        raise GuideError("楽天トラベル設定の版または提供元が不正です")
    approvals = config.get("approvals")
    if not isinstance(approvals, dict):
        raise GuideError("API利用審査設定が不正です")
    return (config.get("enabled") is True and config.get("api_fetch_enabled") is True
            and approvals.get("travel_api_access_confirmed") is True
            and approvals.get("rakuten_webservice_data_terms_reviewed") is True)


def _basic_info(entry):
    """Handle known response wrappers without assuming unobserved API records."""
    if not isinstance(entry, dict):
        raise GuideError("ホテルデータの構造が不正です")
    if "hotel" in entry:
        hotel = entry["hotel"]
        if isinstance(hotel, list):
            basic = next((x["hotelBasicInfo"] for x in hotel
                          if isinstance(x, dict) and isinstance(x.get("hotelBasicInfo"), dict)), None)
        elif isinstance(hotel, dict):
            basic = hotel.get("hotelBasicInfo")
        else:
            basic = None
    else:
        basic = entry.get("hotelBasicInfo")
    if not isinstance(basic, dict):
        raise GuideError("施設基本情報がありません")
    return basic


def _safe_rakuten_url(url):
    safe_url(url)
    host = urlsplit(url).hostname
    if host != "rakuten.co.jp" and not host.endswith(".rakuten.co.jp"):
        raise GuideError("楽天ドメイン以外の施設リンクは拒否します")
    return url


def normalize_hotel_snapshot(snapshot, fetched_at):
    """Review-only candidate list. Never store prices, images or review text.

    Even if the API call included affiliateId, affiliation is not inferred
    from the mere existence of hotelInformationUrl. A separate approval is
    needed before a link is published.
    """
    parse_time(fetched_at)
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("hotels"), list):
        raise GuideError("楽天トラベル施設一覧の形式が不正です")
    rows = snapshot["hotels"]
    if len(rows) > MAX_HOTELS:
        raise GuideError("候補施設が1回の審査上限を超えています")
    normalized = []
    seen = set()
    for entry in rows:
        basic = _basic_info(entry)
        try:
            raw_no = basic["hotelNo"]
            name = basic["hotelName"]
            url = basic["hotelInformationUrl"]
        except KeyError as exc:
            raise GuideError("必須の施設情報がありません") from exc
        if isinstance(raw_no, bool) or not str(raw_no).isdigit():
            raise GuideError("施設番号の形式が不正です")
        number = int(raw_no)
        if number <= 0 or number > 9999999999 or number in seen:
            raise GuideError("施設番号が重複または不正です")
        if (not isinstance(name, str) or not name.strip() or len(name) > 160
                or "<" in name or ">" in name or "\x00" in name):
            raise GuideError("施設名の形式が不正です")
        _safe_rakuten_url(url)
        seen.add(number)
        normalized.append({
            "hotel_no": number, "hotel_name": name.strip(), "source_url": url,
            "checked_at": fetched_at,
            "review_state": "needs_family_capacity_and_terms_review",
            "can_accommodate_party": None,
            "family_total_jpy": None,
            "room_count": None,
            "affiliate_link_verified": False,
            "publishable": False
        })
    return normalized


def approve_exact_booking_quote(quote):
    """Allow a family total ONLY with dates, ages/occupancy, rooms and evidence.

    Does not cause any public page to be generated; the caller still needs
    copyright and site-registration approval.
    """
    from datetime import date
    if not isinstance(quote, dict):
        raise GuideError("宿泊見積条件が不正です")
    required = ("checkin_date", "checkout_date", "adults", "children_ages",
                "rooms", "meal_plan", "verified_at", "family_total_jpy",
                "official_plan_url")
    if any(key not in quote for key in required):
        raise GuideError("宿泊料金の人数・日付・部屋条件が不足しています")
    try:
        checkin = date.fromisoformat(quote["checkin_date"])
        checkout = date.fromisoformat(quote["checkout_date"])
    except (TypeError, ValueError) as exc:
        raise GuideError("宿泊日付が不正です") from exc
    if checkout <= checkin:
        raise GuideError("チェックアウト日はチェックイン後が必要です")
    if (type(quote["adults"]) is not int or quote["adults"] < 1
            or type(quote["rooms"]) is not int or quote["rooms"] < 1
            or type(quote["family_total_jpy"]) is not int or quote["family_total_jpy"] <= 0):
        raise GuideError("人数・室数・料金の形式が不正です")
    ages = quote["children_ages"]
    if (not isinstance(ages, list) or len(ages) + quote["adults"] not in (4, 5, 6)
            or any(type(age) is not int or age < 0 or age > 17 for age in ages)
            or not isinstance(quote["meal_plan"], str) or not quote["meal_plan"].strip()):
        raise GuideError("4〜6名分の年齢・食事条件が不足しています")
    verified = parse_time(quote["verified_at"])
    safe_url(quote["official_plan_url"])
    return {"family_total_jpy": quote["family_total_jpy"],
            "checkin_date": quote["checkin_date"],
            "checkout_date": quote["checkout_date"],
            "booking_basis_verified_at": verified.isoformat(),
            "price_is_fixed": False}
