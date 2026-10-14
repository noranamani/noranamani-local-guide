"""JSON schema plus cross-record, provenance, privacy and date validation."""
import re
from datetime import timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from .core import GuideError, occurrence_bounds, parse_fact_time, parse_time, read_json, safe_url
from .sources import approved

SECRET = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
SECRET_KEY = re.compile(r"(?i)^(?:password|secret|api[_-]?key|access[_-]?token|private[_-]?key)$")


def inspect_text(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.match(key) and item:
                raise GuideError("秘密値の可能性がある項目を検出しました")
            inspect_text(item)
    elif isinstance(value, list):
        for item in value:
            inspect_text(item)
    elif isinstance(value, str):
        if SECRET.search(value) or "\ufffd" in value or "\x00" in value:
            raise GuideError("秘密値・文字化け・制御文字の可能性を検出しました")


def schema_check(root, name, data):
    schema = read_json(root / f"schemas/{name}.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda error: str(list(error.path)))
    if errors:
        # Values are intentionally excluded from exception messages.
        error = errors[0]
        location = "/".join(str(k) for k in error.path) or "root"
        raise GuideError(f"{name}: スキーマ違反 ({location}, {error.validator})")
    inspect_text(data)


def validate_config(root, now):
    areas = read_json(root / "config/areas.json")
    categories = read_json(root / "config/categories.json")
    rules = read_json(root / "config/page_rules.json")
    config = read_json(root / "config/sources.json")
    for name, value in (("areas", areas), ("categories", categories), ("page_rules", rules), ("sources", config)):
        schema_check(root, name, value)
        if value.get("schema_version") != 1:
            raise GuideError(f"{name}: 未対応のスキーマ版です")
        inspect_text(value)
    for collection in (areas["areas"], categories["primary"], config["sources"]):
        ids = [v["id"] for v in collection]
        if len(ids) != len(set(ids)) or not all(re.fullmatch(r"[a-z0-9_-]+", value) for value in ids):
            raise GuideError("設定IDが重複または不正です")
    if rules["timezone"] != "Asia/Tokyo":
        raise GuideError("運用タイムゾーンはAsia/Tokyoのみです")
    if rules["site_url"] is not None:
        safe_url(rules["site_url"])
        if "?" in rules["site_url"]:
            raise GuideError("site_urlにはクエリを指定できません")
    safety = rules["publication"]
    if any(safety.get(k) is not True for k in ("require_verified_source", "exclude_cancelled",
           "exclude_expired_occurrences", "unknown_price_is_not_free", "unknown_date_is_not_event")):
        raise GuideError("公開の安全条件は無効化できません")
    if (rules["seo"]["empty_draft_pages_public"] is not False
            or rules["list_pages"]["avoid_thin_pages"] is not True):
        raise GuideError("空ページ・薄いページの公開は許可されません")
    for source in config["sources"]:
        if source["area"] not in {a["id"] for a in areas["areas"]} | {"multiple"}:
            raise GuideError("情報源の地域IDが不正です")
        if type(source["enabled"]) is not bool:
            raise GuideError("enabledは真偽値で指定してください")
        safe_url(source["url"])
        if source["enabled"]:
            approved(source, now)
    return areas, categories, rules, config


def validate_dataset(root, name, dataset, now):
    schema_check(root, name, dataset)
    areas, categories, _, config = validate_config(root, now)
    sources = {s["id"]: s for s in config["sources"]}
    area_names = {a["id"] for a in areas["areas"]} | {a["name"] for a in areas["areas"]}
    category_ids = {c["id"] for c in categories["primary"]}
    id_key = {"events": "event_id", "places": "place_id", "offers": "offer_id", "store_news": "news_id"}.get(name)
    if id_key:
        ids = [r[id_key] for r in dataset["items"]]
        if len(ids) != len(set(ids)):
            raise GuideError(f"{name}: レコードIDが重複しています")
    for record in dataset.get("items", []):
        if "municipality" in record and record["municipality"] not in area_names:
            raise GuideError("未登録の自治体です")
        if "category_ids" in record and not set(record["category_ids"]) <= category_ids:
            raise GuideError("未登録のカテゴリです")
        for key in ("title", "name", "location_label", "age_info", "price_description", "address"):
            value = record.get(key)
            if value and any(c in value for c in "<>\n\r"):
                raise GuideError("本文・HTML・改行を事実欄に保存できません")
        for key in ("first_seen_at", "last_verified_at"):
            if record.get(key) and parse_time(record[key]) > now:
                raise GuideError("確認日時が未来です")
        if record.get("first_seen_at") and parse_time(record["first_seen_at"]) > parse_time(record["last_verified_at"]):
            raise GuideError("初回発見が最終確認より後です")
        for key in ("official_url", "source_url"):
            if record.get(key):
                safe_url(record[key])
        occurrences = record.get("occurrences", [])
        occurrence_ids = [o["occurrence_id"] for o in occurrences]
        if len(occurrence_ids) != len(set(occurrence_ids)):
            raise GuideError("開催回IDが重複しています")
        for occurrence in occurrences:
            occurrence_bounds(occurrence)
        for source in record.get("sources", []):
            sid = source["source_id"]
            if sid not in sources:
                raise GuideError("未登録の情報源です")
            safe_url(source["url"])
            for key in ("fetched_at", "last_checked_at", "source_published_at"):
                parse = parse_fact_time if key == "source_published_at" else parse_time
                if source[key] and parse(source[key]) > now:
                    raise GuideError("情報源の日時が未来です")
            if parse_time(source["last_checked_at"]) < parse_time(source["fetched_at"]):
                raise GuideError("確認日時が取得日時より前です")
            if source["is_primary"] != (sources[sid]["organization_type"] in ("municipality", "organizer", "commercial_facility")):
                raise GuideError("一次情報の区分が設定と一致しません")
            if name == "places" and record.get("address") and sources[sid].get("address_scope") != "public_facilities_only":
                raise GuideError("施設住所の公開範囲が未審査です")
        if record.get("sources") and parse_time(record["last_verified_at"]) > max(parse_time(s["last_checked_at"]) for s in record["sources"]):
            raise GuideError("最終確認日時に根拠となる情報源の確認がありません")
    if name == "source_state" and not set(dataset["sources"]) <= set(sources):
        raise GuideError("取得状態に未登録の情報源があります")


def validate_data(root, now):
    validate_config(root, now)
    datasets = {}
    for name in ("events", "places", "offers", "store_news", "editorial", "note-weekly", "source_state"):
        datasets[name] = read_json(root / f"data/{name}.json")
        validate_dataset(root, name, datasets[name], now)
    events = {e["event_id"] for e in datasets["events"]["items"]}
    places = {p["place_id"] for p in datasets["places"]["items"]}
    for event in datasets["events"]["items"]:
        if event["place_id"] is not None and event["place_id"] not in places:
            raise GuideError("イベントの施設参照が不正です")
    for name in ("editorial", "note-weekly"):
        if not set(datasets[name]["featured_event_ids"]) <= events:
            raise GuideError("編集データに存在しないイベントIDがあります")
    if any(h["event_id"] not in events for h in datasets["editorial"]["highlights"]):
        raise GuideError("編集ハイライトに存在しないイベントIDがあります")
    return datasets


def publishable(record, sources, now, stale_hours):
    if record.get("review_hold"):
        return False
    if now - parse_time(record["last_verified_at"]) > timedelta(hours=stale_hours):
        return False
    # All contributing sources must still be approved; stale/conflicting attributes cannot be laundered.
    for provenance in record["sources"]:
        try:
            approved(sources[provenance["source_id"]], now)
            if now - parse_time(provenance["last_checked_at"]) > timedelta(hours=stale_hours):
                return False
        except GuideError:
            return False
    return True
