"""Offline, approved-source RSS URL discovery: not an event publication pipeline.

The module accepts a local XML snapshot only. It never downloads an RSS feed,
article or image and never writes to public data/ or docs/.
"""
import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

from .core import GuideError, atomic_json, parse_time, read_json, safe_url, serialized

MAX_XML_BYTES = 1024 * 1024
MAX_ITEMS = 150
MAX_QUEUE = 2000
EVENT_WORDS = ("イベント", "マルシェ", "フェス", "祭", "ワークショップ",
               "体験", "ショー", "縁日", "キッズ", "子ども", "こども", "開催")
STORE_WORDS = ("開店", "閉店", "オープン", "リニューアル", "セール", "特売")


def _local_tag(tag):
    return tag.rsplit("}", 1)[-1].lower()


def _text(item, tags):
    for child in item:
        if _local_tag(child.tag) in tags and child.text:
            return child.text.strip()
    return ""


def _link(item, feed_format):
    for child in item:
        if _local_tag(child.tag) != "link":
            continue
        if feed_format == "feed":
            if child.get("rel", "alternate") == "alternate" and child.get("href"):
                return child.get("href").strip()
        elif child.text:
            return child.text.strip()
    return ""


def _article_date(item):
    for child in item:
        if _local_tag(child.tag) not in ("pubdate", "published", "updated", "date"):
            continue
        value = (child.text or "").strip()
        if not value:
            continue
        try:
            point = parsedate_to_datetime(value)
            if point.tzinfo:
                return point.date().isoformat()
        except (ValueError, TypeError, IndexError):
            pass
        try:
            return parse_time(value).date().isoformat()
        except GuideError:
            pass
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            from datetime import date
            try:
                return date.fromisoformat(value).isoformat()
            except ValueError:
                pass
    return None


def _label(title):
    """Heuristic *only*; classification never implies a confirmed event."""
    if any(word in title for word in EVENT_WORDS):
        return "possibly_event"
    if any(word in title for word in STORE_WORDS):
        return "possibly_store_news"
    return None


def _first_party(article_url, feed_url):
    try:
        safe_url(article_url)
        return urlsplit(article_url).hostname == urlsplit(feed_url).hostname
    except GuideError:
        return False


def extract_candidates(body, source_id, feed_url, seen_at):
    """Return only first-party URLs, hashes, publication dates and review flags.

    Copyrighted titles, excerpts, media and XML content are never persisted.
    The RSS published date is NEVER treated as an event date.
    """
    safe_url(feed_url)
    if not isinstance(body, bytes) or not body or len(body) > MAX_XML_BYTES:
        raise GuideError("RSSスナップショットの容量が不正です")
    upper = body.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise GuideError("DTDまたは外部実体を含むXMLは処理しません")
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise GuideError("RSSが不正なXMLです") from exc
    form = _local_tag(root.tag)
    if form not in ("rss", "rdf", "feed"):
        raise GuideError("RSS2.0、RSS1.0/RDFまたはAtom以外のXMLです")
    item_tag = "entry" if form == "feed" else "item"
    items = [item for item in root.iter() if _local_tag(item.tag) == item_tag]
    if len(items) > MAX_ITEMS:
        raise GuideError("RSS記事数が検査上限を超えました")
    records = {}
    for item in items:
        title = _text(item, {"title"})[:200]
        label = _label(title)
        link = _link(item, form)
        if not label or not _first_party(link, feed_url):
            continue
        digest = hashlib.sha256((source_id + "\0" + link).encode("utf-8")).hexdigest()[:24]
        records[digest] = {
            "candidate_id": digest, "source_id": source_id,
            "article_url": link, "article_published_at": _article_date(item),
            "discovered_at": seen_at.isoformat(), "last_seen_at": seen_at.isoformat(),
            "candidate_kind": label, "review_state": "needs_primary_confirmation",
            "publishable": False
        }
    return list(records.values())


def reviewed_for_discovery(source, now):
    """Separate internal feed discovery consent from publication consent."""
    if source.get("kind") != "general_news_rss":
        raise GuideError("RSS候補として登録された情報源ではありません")
    if source.get("rss_discovery_review_status") != "allowed":
        raise GuideError("RSSの内部発見用途について利用条件が未確認です")
    if source.get("terms_review_status") != "allowed" or source.get("robots_review_status") != "allowed":
        raise GuideError("利用規約とrobotsの審査が未完了です")
    permission = source.get("rss_discovery_permission_document")
    safe_url(permission)
    checked = parse_time(source.get("rss_discovery_checked_at"))
    if checked > now or now - checked > timedelta(days=30):
        raise GuideError("RSSの利用審査が30日以内に実施されていません")
    safe_url(source["url"])


@serialized
def stage_snapshot(root, source_id, snapshot_path, now):
    """Review a *manually supplied* XML snapshot, never issue HTTP requests."""
    root = Path(root)
    config = read_json(root / "config/sources.json")
    source = next((s for s in config["sources"] if s["id"] == source_id), None)
    if source is None:
        raise GuideError("登録済みの情報源ではありません")
    reviewed_for_discovery(source, now)
    data = Path(snapshot_path).read_bytes()
    candidates = extract_candidates(data, source_id, source["url"], now)
    target = root / "cache/rss_discovery_queue.json"
    previous = read_json(target) if target.exists() else {"schema_version": 1, "items": []}
    old_items = previous.get("items")
    if previous.get("schema_version") != 1 or not isinstance(old_items, list):
        raise GuideError("確認待ちキューの形式が不正です")
    combined = {x["candidate_id"]: x for x in old_items}
    for record in candidates:
        if record["candidate_id"] in combined:
            old = combined[record["candidate_id"]]
            record["discovered_at"] = old["discovered_at"]
            record["review_state"] = old["review_state"]
            record["publishable"] = False
        combined[record["candidate_id"]] = record
    if len(combined) > MAX_QUEUE:
        raise GuideError("確認待ちキューが上限を超えています")
    atomic_json(target, {"schema_version": 1, "items": sorted(combined.values(), key=lambda x: x["candidate_id"])})
    return {"discovered": len(candidates), "queued": len(combined)}
