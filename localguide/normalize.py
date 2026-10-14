"""Normalize only configured factual CSV columns; never infer unknown facts."""
import csv
import hashlib
import io
import re
import unicodedata
from copy import deepcopy

from .core import GuideError, occurrence_bounds, parse_fact_time, parse_time, safe_url


def identifier(*values):
    return hashlib.sha256("\0".join(values).encode()).hexdigest()[:24]


def title_key(value):
    text = unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in text if not c.isspace() and not unicodedata.category(c).startswith("P"))


def text(value, limit=160):
    value = unicodedata.normalize("NFC", (value or "").strip())
    if len(value) > limit or any(c in value for c in "<>\ufffd") or any(ord(c) < 32 for c in value):
        raise GuideError("事実欄に本文・HTML・制御文字・過長な文章を保存できません")
    return value


def csv_records(body, source, fetched_at):
    adapter = source["adapter"]
    if adapter not in ("event_csv", "places_csv"):
        raise GuideError("未対応のCSVアダプターです")
    mapping = source["field_map"]
    allowed = {"source_event_id", "title", "name", "municipality", "official_url", "source_published_at",
               "start_at", "end_at", "status", "location_label", "age_info", "price_type", "price_description",
               "indoor_outdoor", "address", "organizer_label"}
    if not set(mapping) <= allowed:
        raise GuideError("審査対象の事実列以外はマッピングできません")
    required = {"source_event_id", "title", "municipality", "official_url"} if adapter == "event_csv" else {
        "source_event_id", "name", "municipality", "official_url"}
    if not required <= mapping.keys():
        raise GuideError("CSVの必須列マッピングがありません")
    encoding = source.get("encoding", "utf-8-sig")
    if encoding not in ("utf-8-sig", "utf-8", "cp932"):
        raise GuideError("未対応の文字コードです")
    try:
        reader = csv.DictReader(io.StringIO(body.decode(encoding)), strict=True)
        if not reader.fieldnames or not set(mapping.values()) <= set(reader.fieldnames):
            raise GuideError("CSVヘッダーが審査済みマッピングと一致しません")
        result = []
        for row in reader:
            if len(result) >= 5000 or None in row or any(v is None for v in row.values()):
                raise GuideError("CSVの列数または件数が不正です")
            fields = {k: text(row[v], 500 if k == "official_url" else 160) for k, v in mapping.items()}
            if any(not fields[k] for k in required):
                raise GuideError("CSVの必須値が空です")
            official_url = safe_url(fields["official_url"])
            published = fields.get("source_published_at") or source.get("source_published_date") or None
            if published:
                parse_fact_time(published)
            provenance = [{"source_id": source["id"], "url": source["url"],
                           "source_event_id": fields["source_event_id"], "fetched_at": fetched_at,
                           "last_checked_at": fetched_at, "source_published_at": published,
                           "is_primary": source["organization_type"] in ("municipality", "organizer", "commercial_facility")}]
            record_id = identifier(source["id"], fields["source_event_id"])
            if adapter == "places_csv":
                # Address publication needs a separate documented public-facility scope review.
                if fields.get("address") and source.get("address_scope") != "public_facilities_only":
                    raise GuideError("施設住所の公開範囲が未審査です")
                result.append({"place_id": record_id, "name": fields["name"], "municipality": fields["municipality"],
                               "address": fields.get("address") or None, "indoor_outdoor": "unknown", "admission": None,
                               "official_url": official_url, "sources": provenance, "last_verified_at": fetched_at})
                continue
            occurrences = [{"occurrence_id": identifier(record_id, fields.get("start_at", ""), fields.get("end_at", "")),
                            "start_at": fields.get("start_at") or None, "end_at": fields.get("end_at") or None,
                            "timezone": "Asia/Tokyo", "status": fields.get("status") or "unconfirmed"}]
            occurrence_bounds(occurrences[0])
            price = fields.get("price_type") or "unknown"
            if price not in ("free", "paid", "conditional", "unknown"):
                raise GuideError("料金区分は審査済みの明示値のみ使用できます")
            if price == "free" and source.get("free_value_reviewed") is not True:
                raise GuideError("無料の定義が未審査です")
            result.append({"event_id": record_id, "title": fields["title"], "municipality": fields["municipality"],
                           "official_url": official_url,
                           "place_id": None, "location_label": fields.get("location_label") or None,
                           "category_ids": source.get("category_ids", ["event"]), "occurrences": occurrences,
                           "age_info": fields.get("age_info") or None, "indoor_outdoor": fields.get("indoor_outdoor") or "unknown",
                           "price_type": price, "price_description": fields.get("price_description") or None,
                           "reservation_required": None, "sources": provenance, "first_seen_at": fetched_at,
                           "organizer_label": fields.get("organizer_label") or None,
                           "review_hold": False,
                           "last_verified_at": fetched_at, "status": fields.get("status") or "unconfirmed"})
        ids = [r.get("event_id", r.get("place_id")) for r in result]
        if len(ids) != len(set(ids)):
            raise GuideError("同一ソースのIDが重複しています（開催回を勝手に統合しません）")
        return result
    except UnicodeError as exc:
        raise GuideError("CSVの文字コードが不正です") from exc
    except csv.Error as exc:
        raise GuideError("CSVの引用符・フィールド長・構文が不正です") from exc


def same_occurrences(left, right):
    def signature(event):
        return sorted((o["start_at"], o["end_at"] or "", o["status"]) for o in event["occurrences"] if o["start_at"])
    a, b = signature(left), signature(right)
    return bool(a) and a == b and len(a) == len(left["occurrences"]) == len(right["occurrences"])


def merge_events(existing, incoming):
    """Matching title without dates/place is held for review; never publish conflicts."""
    result, reviews = deepcopy(existing), []
    for event in incoming:
        source_ids = {(s["source_id"], s["source_event_id"]) for s in event["sources"]}
        same_source = [old for old in result if source_ids & {(s["source_id"], s["source_event_id"]) for s in old["sources"]}]
        if same_source:
            old = same_source[0]
            if len(old["sources"]) == 1 and len(same_source) == 1:
                event = deepcopy(event)
                event["event_id"] = old["event_id"]
                event["first_seen_at"] = old["first_seen_at"]
                event["review_hold"] = old.get("review_hold", False)
                if event["review_hold"]:
                    event["status"] = "unconfirmed"
                result[result.index(old)] = event
                continue
            matches = same_source
        else:
            matches = [old for old in result if title_key(old["title"]) == title_key(event["title"])]
        exact = [old for old in matches if same_occurrences(old, event)
                 and old["municipality"] == event["municipality"]
                 and old["location_label"] and old["location_label"] == event["location_label"]]
        facts = ("price_type", "price_description", "indoor_outdoor", "age_info", "reservation_required", "status",
                 "organizer_label", "category_ids", "place_id")
        if len(exact) == 1 and len(matches) == 1 and all(exact[0].get(k) == event.get(k) for k in facts):
            old = exact[0]
            old["sources"] = [s for s in old["sources"] if (s["source_id"], s["source_event_id"]) not in source_ids] + deepcopy(event["sources"])
            old["last_verified_at"] = max(old["last_verified_at"], event["last_verified_at"], key=parse_time)
        elif matches:
            event = deepcopy(event)
            event["status"] = "unconfirmed"
            event["review_hold"] = True
            for old in matches:
                old["status"] = "unconfirmed"
                old["review_hold"] = True
            collision = next((old for old in result if old["event_id"] == event["event_id"]), None)
            if collision:
                collision["sources"] = [s for s in collision["sources"]
                                        if (s["source_id"], s["source_event_id"]) not in source_ids] + deepcopy(event["sources"])
            else:
                result.append(event)
            reviews.append({"event_id": event["event_id"], "candidate_ids": [o["event_id"] for o in matches],
                            "incoming": deepcopy(event),
                            "reason": "日時・場所・属性の不一致または不足。手動確認が必要"})
        else:
            result.append(deepcopy(event))
    return result, reviews
