"""Owner-curated, permanent nearby outings; no crawling or borrowed images."""
from datetime import date
from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit

from .core import GuideError, read_json, safe_url
from .validation import inspect_text

APPROVED_HOSTS = frozenset({
    "kako-navi.jp",
    "www.city.kakogawa.lg.jp",
    "kakogawa-mcc.com",
    "www.town.harima.lg.jp",
    "www.city.akashi.lg.jp",
    "e-akashi.jp",  # Park operator linked from Akashi City's official guidance
})
FIELDS = frozenset({
    "id", "name", "municipality", "type",
    "official_url", "idea", "before_you_go",
})

# Fixed mapping reviewed against the owner's nearby_image_manifest.json.
# The manifest is audit evidence, not an arbitrary path/HTML configuration input.
NEARBY_IMAGES = {
    "hero": ("nearby-hero.webp", "近場のおでかけの雰囲気を表現したAI生成のイメージイラスト（実際の風景ではありません）", 1440, 810),
    "gongen-park": ("nearby-gongen-park.webp", "大型遊具のある公園を表現したAI生成のイメージイラスト（実際の権現総合公園の写真ではありません）", 960, 540),
    "mitoro-hill": ("nearby-mitoro-hill.webp", "温室と緑の広場を表現したAI生成のイメージイラスト（実際のみとろの丘の写真ではありません）", 960, 540),
    "hiokayama-park": ("nearby-hiokayama-park.webp", "緑の広場と散策路を表現したAI生成のイメージイラスト（実際の日岡山公園の写真ではありません）", 960, 540),
    "hamanomiya-park": ("nearby-hamanomiya-park.webp", "芝生と木々のある公園を表現したAI生成のイメージイラスト（実際の浜の宮公園の写真ではありません）", 960, 540),
    "kakogawa-marine-center": ("nearby-kakogawa-marine-center.webp", "海辺の学びの施設を表現したAI生成のイメージイラスト（実際の加古川海洋文化センターの外観・設備ではありません）", 960, 540),
    "onaka-ruins-park": ("nearby-onaka-ruins-park.webp", "復元された古代の住居と散策風景を表現したAI生成のイメージイラスト（実際の大中遺跡公園の写真ではありません）", 960, 540),
    "ishigatani-park": ("nearby-ishigatani-park.webp", "遊具と緑のある公園を表現したAI生成のイメージイラスト（実際の石ケ谷公園の写真ではありません）", 960, 540),
    "kakurinji-park": ("nearby-kakurinji-park.webp", "公園の蒸気機関車と散策風景を表現したAI生成のイメージイラスト（実際の鶴林寺公園の写真ではありません）", 960, 540),
    "shikata-east-park": ("nearby-shikata-east-park.webp", "芝生広場でくつろぐ風景を表現したAI生成のイメージイラスト（実際の志方東公園の写真ではありません）", 960, 540),
}
HOME_FEATURES = ("gongen-park", "hamanomiya-park", "mitoro-hill",
                 "kakogawa-marine-center", "onaka-ruins-park", "kakurinji-park")
IMAGE_NOTICE = "AI生成のイメージ画像（実際の施設写真ではありません）"


def nearby_image(spot_id, *, hero=False):
    """A fixed local image and adjacent notice; never infer facts from artwork."""
    filename, alt, width, height = NEARBY_IMAGES[spot_id]
    kind = "hero" if hero else "card"
    priority = ' loading="eager" fetchpriority="high"' if hero else ' loading="lazy"'
    return (
        f'<figure class="nearby-image nearby-image--{kind}">'
        f'<img class="nearby-image__img" src="{filename}" alt="{escape(alt, quote=True)}" '
        f'width="{width}" height="{height}"{priority} decoding="async">'
        f'<figcaption>{IMAGE_NOTICE}</figcaption></figure>'
    )


def nearby_preview_cards(items):
    """Link six visual entry points to the existing, reviewed facility guidance."""
    by_id = {item["id"]: item for item in items}
    cards = []
    for spot_id in HOME_FEATURES:
        item = by_id.get(spot_id)
        if item is None:
            continue
        name = escape(item["name"], quote=True)
        cards.append(
            '<article class="card nearby-preview-card">'
            f'<a class="nearby-preview-card__link" href="nearby.html#{spot_id}">'
            + nearby_image(spot_id) + '<div class="nearby-preview-card__body">'
            f'<p class="nearby-preview-card__meta">{escape(item["municipality"])}'
            f'<span aria-hidden="true"> · </span>{escape(item["type"])}</p>'
            f'<h3>{name}</h3><p class="nearby-preview-card__description">'
            f'{escape(item["idea"])}</p>'
            '<span class="nearby-preview-card__more">おでかけのヒントを見る '
            '<span aria-hidden="true">→</span></span></div></a></article>'
        )
    return "".join(cards)


def reviewed_nearby(root):
    """Read only committed, manually checked links; never fetch external URLs.

    Missing data is an empty collection to keep synthetic/older test workspaces
    valid. Malformed or unsafe present data fails closed.
    """
    path = Path(root) / "data/nearby_spots.json"
    if not path.is_file():
        return []
    raw = read_json(path)
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise GuideError("近場ガイドのデータ形式が不正です")
    if raw.get("editorial_policy") != "manual_official_links_only":
        raise GuideError("手動確認済みリンクだけ掲載できます")
    try:
        date.fromisoformat(raw["reviewed_on"])
    except (ValueError, KeyError, TypeError) as exc:
        raise GuideError("近場ガイドの確認日が不正です") from exc
    items = raw.get("items")
    if not isinstance(items, list) or not 0 <= len(items) <= 20:
        raise GuideError("近場ガイドの掲載件数が不正です")
    inspect_text(raw)
    ids = set()
    for record in items:
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise GuideError("近場ガイドの項目が不足・過剰です")
        for field in FIELDS - {"official_url"}:
            value = record[field]
            if not isinstance(value, str) or not 1 <= len(value) <= 240:
                raise GuideError("近場ガイドに不正な本文があります")
            if any(ch in value for ch in "<>\r\n\x00"):
                raise GuideError("近場ガイドの本文にHTMLまたは改行を含みます")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", record["id"]):
            raise GuideError("近場ガイドIDが不正です")
        if record["id"] in ids:
            raise GuideError("近場ガイドIDが重複しています")
        ids.add(record["id"])
        url = safe_url(record["official_url"])
        parts = urlsplit(url)
        if parts.hostname not in APPROVED_HOSTS or parts.query or parts.fragment:
            raise GuideError("近場ガイドのリンク先は確認済み公式サイトに限定します")
    return items


def nearby_cards(items):
    """Escape all fields, expose unknown prices, and link to original sources."""
    cards = []
    for item in items:
        name = escape(item["name"], quote=True)
        municipality = escape(item["municipality"], quote=True)
        category = escape(item["type"], quote=True)
        idea = escape(item["idea"], quote=True)
        caution = escape(item["before_you_go"], quote=True)
        url = escape(item["official_url"], quote=True)
        cards.append(
            f'<article class="card nearby-card" id="{escape(item["id"], quote=True)}">'
            + nearby_image(item["id"]) + '<div class="nearby-card__body">'
            f'<p class="nearby-card__meta"><span class="tag">{municipality}</span> '
            f'<span class="tag">{category}</span></p>'
            f'<h2>{name}</h2>'
            f'<p>{idea}</p>'
            f'<p><strong>出かける前に</strong>：{caution}</p>'
            '<p class="muted">料金・営業時間・年齢条件：施設ごとに公式案内で確認</p>'
            f'<p><a class="nearby-card__official" href="{url}" rel="noopener noreferrer">'
            f'{name}の公式案内を見る →</a></p></div></article>'
        )
    return "".join(cards)


def nearby_page_body(items, reviewed_on):
    reviewed = escape(reviewed_on, quote=True)
    return (
        nearby_image("hero", hero=True)
        + '<section class="listing-lead" aria-label="近場のよりみちの探し方">'
        '<span class="section-kicker">NEARBY OUTINGS</span>'
        '<p>公園・屋内施設・歴史にふれる場所を、公式案内へのリンク付きで紹介します。'
        'お出かけのヒントは当サイトの独自編集で、第三者の写真・文章は転載していません。</p>'
        '<p class="listing-lead__disclaimer">掲載は定番の行き先候補です。'
        '今日の営業・開催イベント・混雑・無料利用を保証するものではありません。'
        '行く前に必ず施設の公式サイトで最新情報をお確かめください。</p>'
        f'<p class="muted">公式リンクの最終編集確認日：{reviewed}</p>'
        '</section><div class="cards nearby-grid">'
        + nearby_cards(items) + '</div>'
    )
