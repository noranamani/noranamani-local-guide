"""Curated official event directory: human-reviewed links, no network collection."""
from datetime import date
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import GuideError, read_json, safe_url
from .validation import inspect_text

OFFICIAL_HOSTS = frozenset({
    "www.city.kakogawa.lg.jp",
    "www.city.himeji.lg.jp",
    "www.city.akashi.lg.jp",
    "www.yokoso-akashi.jp",
    "hyogo-akashipark.jp",
    "web.pref.hyogo.lg.jp",
})
FIELDS = frozenset({"id", "name", "municipality", "category", "url", "summary"})


def official_event_links(root):
    """Read owner-reviewed outbound links only; never access their websites."""
    path = Path(root) / "data/official_event_links.json"
    if not path.exists():
        return [], None
    raw = read_json(path)
    if (not isinstance(raw, dict)
            or set(raw) != {"schema_version", "policy", "reviewed_on", "items"}
            or raw["schema_version"] != 1
            or raw["policy"] != "manual_official_links_only"):
        raise GuideError("公式イベントリンク集の形式または公開方針が不正です")
    try:
        date.fromisoformat(raw["reviewed_on"])
    except (TypeError, ValueError) as exc:
        raise GuideError("公式イベントリンクの確認日が不正です") from exc
    items = raw["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise GuideError("公式イベントリンクの件数が不正です")
    inspect_text(raw)
    ids, urls = set(), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise GuideError("公式イベントリンクの項目が不正です")
        for key in FIELDS - {"url"}:
            value = item[key]
            if (not isinstance(value, str) or not 1 <= len(value) <= 180
                    or any(ch in value for ch in "<>\r\n\x00")):
                raise GuideError("公式イベントリンクに不正な文言があります")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"]):
            raise GuideError("公式イベントリンクのIDが不正です")
        url = safe_url(item["url"])
        if urlsplit(url).hostname not in OFFICIAL_HOSTS:
            raise GuideError("イベントリンクは審査済みの公式ドメインに限定します")
        if item["id"] in ids or url in urls:
            raise GuideError("公式イベントリンクが重複しています")
        ids.add(item["id"])
        urls.add(url)
    return items, raw["reviewed_on"]


def event_finder_body(links, reviewed_on, curated_cards=""):
    """Render verified local entries separately from outbound official directories."""
    curated_section = (
        '<section class="home-section" aria-label="個別の開催情報">'
        '<h2>主催者公式で確認した開催情報</h2>'
        '<p>開催日と会場を人手で確認し、期限内のものだけご案内しています。</p>'
        '<div class="cards">' + curated_cards + '</div></section>'
        if curated_cards else '<p class="muted">個別イベントの掲載は現在準備中です。下記の公式案内からお探しください。</p>'
    )
    cards = []
    for item in links:
        name = escape(item["name"], quote=True)
        area = escape(item["municipality"], quote=True)
        kind = escape(item["category"], quote=True)
        summary = escape(item["summary"], quote=True)
        url = escape(item["url"], quote=True)
        cards.append(
            f'<article class="card event-source-card" id="{escape(item["id"], quote=True)}">'
            f'<p class="muted">{area}／{kind}</p><h2>{name}</h2>'
            f'<p>{summary}</p><p><a href="{url}" rel="noopener noreferrer">'
            '公式イベント案内を確認する →</a></p></article>'
        )
    return (
        curated_section + '<section class="listing-lead" aria-label="公式イベントの探し方">'
        '<span class="section-kicker">EVENT GUIDE</span>'
        '<p>地域の公式イベント案内をまとめました。リンク先で今後の開催情報を探せます。</p>'
        '<p class="listing-lead__disclaimer">当サイトがイベント日程や空席を自動取得・転載しているわけではありません。'
        '日付・料金・対象・予約条件・中止は各主催者の最新の案内をご確認ください。</p>'
        f'<p class="muted">リンクの最終編集確認日：{escape(reviewed_on, quote=True)}</p>'
        '</section><div class="cards">'
        + "".join(cards) + '</div>'
    )
