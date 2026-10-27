"""Reviewed *links* to independent local event information sites.

No article text, images, RSS extraction, data licensing or website requests.
"""
from datetime import date
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import GuideError, read_json, safe_url
from .validation import inspect_text

POLICY = "outbound_text_links_only"
LINK_POLICY_BY_ID = {
    "kakogawa-note": {
        "host": "kakogawa-note.com",
        "policy_url": "https://kakogawa-note.com/link/",
        "path": "/category/event/",
    },
    "abc-kakogawa": {
        "host": "abc-housing.asahi.co.jp",
        "policy_url": "https://abc-housing.asahi.co.jp/infouse.html",
        "path": "/kinki/campaign/kakogawa/",
    },
}
FIELDS = frozenset({
    "id", "name", "area", "category", "url", "description", "link_policy_url",
})


def reviewed_community_event_sources(root):
    """Return only explicitly reviewed text links; fail on unknown hosts/fields."""
    path = Path(root) / "data/community_event_sources.json"
    if not path.is_file():
        return [], None
    raw = read_json(path)
    if (not isinstance(raw, dict)
            or set(raw) != {"schema_version", "policy", "reviewed_on", "items"}
            or raw["schema_version"] != 1
            or raw["policy"] != POLICY):
        raise GuideError("地域の民間イベントリンクの方針・形式が不正です")
    try:
        if not isinstance(raw["reviewed_on"], str):
            raise ValueError("not a string")
        date.fromisoformat(raw["reviewed_on"])
    except ValueError as exc:
        raise GuideError("地域の民間イベントリンクの確認日が不正です") from exc
    items = raw["items"]
    if not isinstance(items, list) or len(items) != len(LINK_POLICY_BY_ID):
        raise GuideError("地域の民間イベントリンク件数は審査済み2件に限定します")
    inspect_text(raw)
    ids, urls = set(), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise GuideError("地域の民間イベントリンクの項目が不正です")
        for key in FIELDS - {"url", "link_policy_url"}:
            text = item[key]
            if (not isinstance(text, str) or not 1 <= len(text) <= 180
                    or any(c in text for c in "<>\x00\r\n")):
                raise GuideError("地域の民間イベントリンクの文言が不正です")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"]):
            raise GuideError("地域の民間イベントリンクのIDが不正です")
        expected = LINK_POLICY_BY_ID.get(item["id"])
        if not expected:
            raise GuideError("未審査の地域メディアをリンクしようとしています")
        url = safe_url(item["url"])
        parts = urlsplit(url)
        if (parts.hostname != expected["host"] or parts.path != expected["path"]
                or parts.query or parts.fragment):
            raise GuideError("地域メディアの審査済み案内URLと一致しません")
        if safe_url(item["link_policy_url"]) != expected["policy_url"]:
            raise GuideError("地域メディアのリンク利用条件URLが変更されています")
        if item["id"] in ids or url in urls:
            raise GuideError("地域メディアの案内リンクが重複しています")
        ids.add(item["id"])
        urls.add(url)
    return items, raw["reviewed_on"]


def community_event_section(items, reviewed_on):
    """Render visibly separated external source cards, without any embedded assets."""
    if not items:
        return ""
    cards = []
    for item in items:
        item_id = escape(item["id"], quote=True)
        name = escape(item["name"], quote=True)
        area = escape(item["area"], quote=True)
        kind = escape(item["category"], quote=True)
        description = escape(item["description"], quote=True)
        url = escape(item["url"], quote=True)
        policy = escape(item["link_policy_url"], quote=True)
        cards.append(
            f'<article class="card community-event-source-card" id="{item_id}">'
            f'<p class="muted">{area}／{kind}</p>'
            f'<h3>{name}</h3>'
            f'<p>{description}</p>'
            f'<p><a href="{url}" rel="noopener noreferrer">外部のイベント情報を見る →</a></p>'
            f'<p class="muted"><a href="{policy}" rel="noopener noreferrer">リンク利用条件</a></p>'
            '</article>'
        )
    return (
        '<section class="home-section" id="community-event-links" '
        'aria-label="地域の民間イベント情報サイト">'
        '<span class="section-kicker">LOCAL MEDIA & EVENTS</span>'
        '<h2>地域の民間イベント情報サイト</h2>'
        '<p>地域メディアや民間施設のイベント案内へのリンクです。'
        '自治体等の公式イベント案内とは区別して掲載しています。</p>'
        '<p class="muted">本欄は外部情報への紹介であり、各サイトの公認・提携を示すものではありません。'
        '各記事やイベントの開催日・料金・申込条件はリンク先でご確認ください。'
        '記事本文や写真は当サイトに転載していません。</p>'
        f'<p class="muted">リンクの最終編集確認日：{escape(reviewed_on, quote=True)}</p>'
        '<div class="cards">'
        + "".join(cards) + '</div></section>'
    )
