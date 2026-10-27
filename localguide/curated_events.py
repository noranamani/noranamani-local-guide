"""Manually approved factual event listings. No crawling, email ingestion, or API calls."""
from datetime import date, timedelta
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import GuideError, JST, now_jst, parse_time, read_json, safe_url
from .official_event_hub import OFFICIAL_HOSTS
from .validation import inspect_text

FIELDS = frozenset({
    "id", "title", "municipality", "venue", "official_url", "start_on",
    "end_on", "checked_at", "review_state", "review_note", "information_scope",
})
STATES = frozenset({"approved", "needs_recheck", "expired"})
SCOPE = "facts_only_owner_reviewed"


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise GuideError("イベント開催日はYYYY-MM-DDで指定してください")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise GuideError("イベント開催日が不正です") from exc


def _validate_text(value, max_length=200):
    if (not isinstance(value, str) or not 1 <= len(value) <= max_length
            or any(char in value for char in "<>\r\n\x00")):
        raise GuideError("手動イベントに不正な文言があります")


def _validate_events(raw, now):
    if (not isinstance(raw, dict)
            or set(raw) != {"schema_version", "editorial_policy", "items"}
            or raw["schema_version"] != 1
            or raw["editorial_policy"] != "human_review_pr_only"):
        raise GuideError("手動イベントのデータ形式または承認方針が不正です")
    items = raw["items"]
    if not isinstance(items, list) or len(items) > 100:
        raise GuideError("手動イベントの件数が不正です")
    inspect_text(raw)
    ids, urls, occurrence_keys = set(), set(), set()
    for event in items:
        if not isinstance(event, dict) or set(event) != FIELDS:
            raise GuideError("手動イベントの項目が不足または過剰です")
        for key in ("title", "municipality", "venue", "review_note"):
            _validate_text(event[key])
        _validate_text(event["id"], 80)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", event["id"]):
            raise GuideError("手動イベントIDが不正です")
        if event["review_state"] not in STATES or event["information_scope"] != SCOPE:
            raise GuideError("手動承認の状態または事実範囲が不正です")
        url = safe_url(event["official_url"])
        if urlsplit(url).hostname not in OFFICIAL_HOSTS:
            raise GuideError("主催者の公式URLとして審査済みのドメインが必要です")
        start, end = _day(event["start_on"]), _day(event["end_on"])
        if end < start or (end - start).days > 60:
            raise GuideError("開催期間が不正です")
        verified = parse_time(event["checked_at"])
        if verified > now:
            raise GuideError("手動イベントの確認日時が未来です")
        occurrence = (event["municipality"].strip(), event["venue"].strip(),
                      event["title"].strip(), event["start_on"])
        if event["id"] in ids or url in urls or occurrence in occurrence_keys:
            raise GuideError("手動イベントが重複しています")
        ids.add(event["id"])
        urls.add(url)
        occurrence_keys.add(occurrence)
    return items


def read_curated_events(root, now=None):
    """Read and validate all records, including withheld ones, but never publish them."""
    path = Path(root) / "data/curated_events.json"
    if not path.is_file():
        return []
    now = now or now_jst()
    return _validate_events(read_json(path), now)


def event_state(event, now, stale_hours=72):
    """Expiry takes precedence. No automatic extension of the confirmation time."""
    end = _day(event["end_on"])
    if end < now.astimezone(JST).date():
        return "expired"
    if event["review_state"] == "expired":
        return "expired"
    if event["review_state"] == "needs_recheck":
        return "needs_recheck"
    age = now - parse_time(event["checked_at"])
    if age > timedelta(hours=stale_hours):
        return "needs_recheck"
    return "approved"


def public_curated_events(root, now, stale_hours=72):
    items = read_curated_events(root, now)
    active = [item for item in items if event_state(item, now, stale_hours) == "approved"]
    return sorted(active, key=lambda item: (item["start_on"], item["id"]))


def curated_event_cards(events):
    cards = []
    for event in events:
        start = escape(event["start_on"], quote=True)
        end = escape(event["end_on"], quote=True)
        dates = start if start == end else start + " ～ " + end
        title = escape(event["title"], quote=True)
        municipality = escape(event["municipality"], quote=True)
        venue = escape(event["venue"], quote=True)
        official = escape(event["official_url"], quote=True)
        verified = escape(event["checked_at"], quote=True)
        cards.append(
            f'<article class="card curated-event-card" id="{escape(event["id"], quote=True)}">'
            f'<p class="muted">{municipality}／{dates}</p><h2>{title}</h2>'
            f'<p>会場：{venue}</p>'
            '<p>料金・年齢・定員・予約・変更・中止は主催者の公式案内で確認してください。</p>'
            f'<p class="muted">公式案内の最終確認：{verified}</p>'
            f'<p><a href="{official}" rel="noopener noreferrer">主催者の公式案内を確認する →</a></p>'
            '</article>'
        )
    return "".join(cards)
