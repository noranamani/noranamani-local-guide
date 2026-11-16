"""Human-reviewed official facility links beyond the licensed Akashi CSV.

These are editorial outbound text links only: never collected as an external
data source or mixed with the daily CSV/72-hour record freshness.
"""
from datetime import date
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import GuideError, read_json, safe_url
from .validation import inspect_text

FIELDS = frozenset({"id", "name", "municipality", "kind",
                    "official_url", "idea", "before_you_go"})
PATHS = frozenset({"/atom/", "/aqua/", "/dobutuen/"})


def reviewed_facility_links(root):
    path = Path(root) / "data/nearby_facility_links.json"
    if not path.is_file():
        return [], None
    record = read_json(path)
    if (not isinstance(record, dict)
            or set(record) != {"schema_version", "policy", "reviewed_on", "items"}
            or record["schema_version"] != 1
            or record["policy"] != "manual_official_text_links_only"):
        raise GuideError("公式施設の手動リンク一覧が不正です")
    try:
        date.fromisoformat(record["reviewed_on"])
    except (ValueError, TypeError) as exc:
        raise GuideError("公式施設リンクの確認日が不正です") from exc
    items = record["items"]
    if not isinstance(items, list) or not 1 <= len(items) <= 6:
        raise GuideError("公式施設リンクの件数が不正です")
    inspect_text(record)
    seen_ids, seen_urls = set(), set()
    for item in items:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise GuideError("公式施設リンクの項目形式が不正です")
        if item["municipality"] != "姫路市":
            raise GuideError("対象外の自治体です")
        for key in FIELDS - {"official_url"}:
            value = item[key]
            if (not isinstance(value, str) or not 1 <= len(value) <= 200
                    or any(c in value for c in "<>\r\n\x00")):
                raise GuideError("不正な施設案内文があります")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"]):
            raise GuideError("施設リンクIDの形式が不正です")
        url = safe_url(item["official_url"])
        parsed = urlsplit(url)
        if (parsed.hostname != "www.city.himeji.lg.jp"
                or parsed.path not in PATHS or parsed.query or parsed.fragment):
            raise GuideError("未確認の公式施設リンク先です")
        if item["id"] in seen_ids or url in seen_urls:
            raise GuideError("公式施設リンクが重複しています")
        seen_ids.add(item["id"])
        seen_urls.add(url)
    return items, record["reviewed_on"]


def facility_links_section(items, reviewed_on):
    if not items:
        return ""
    cards = []
    for item in items:
        name = escape(item["name"], quote=True)
        cards.append(
            '<article class="card event-source-card">'
            '<p class="muted">' + escape(item["municipality"], quote=True)
            + "／" + escape(item["kind"], quote=True) + '</p>'
            '<h3>' + name + '</h3>'
            '<p>' + escape(item["idea"], quote=True) + '</p>'
            '<p><strong>行く前に</strong>：' + escape(item["before_you_go"], quote=True) + '</p>'
            '<p class="muted">料金・営業日・割引制度は個別の公式案内で確認してください。</p>'
            '<p><a href="' + escape(item["official_url"], quote=True)
            + '" rel="noopener noreferrer">' + name + 'の公式案内を見る →</a></p>'
            '</article>'
        )
    return (
        '<section class="home-section" aria-labelledby="himeji-link-heading">'
        '<div class="home-section__heading"><div>'
        '<span class="section-kicker">HIMEJI OFFICIAL LINKS</span>'
        '<h2 id="himeji-link-heading">姫路へ足を延ばす・公式施設ガイド</h2>'
        '<p>姫路の科学館・水族館・動物園への公式リンクを、写真転載なしで紹介します。'
        '既存の明石市オープンデータとは独立した編集リンクです。</p></div></div>'
        '<p class="muted">公式リンクの最終編集確認日：'
        + escape(reviewed_on, quote=True) + '</p>'
        '<div class="cards">' + "".join(cards) + '</div></section>'
    )
