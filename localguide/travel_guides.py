"""Human-reviewed family travel guide pages; never fetch ads or external content.

Each listed attraction links to its primary/official source. Guides are visibly
marked as preparation drafts until editorial approval, and affiliate links are
deliberately unavailable until site registration and compliance review.
"""
from datetime import timedelta
from html import escape
import re
from urllib.parse import parse_qs, urlsplit

from .core import GuideError, parse_time, safe_url

MAX_SEO_REVIEW_AGE = timedelta(days=90)


def approved_affiliate_html(guide):
    """Accept only an unaltered manually created Rakuten text-link anchor.

    Text-link attributes remain byte-for-byte as submitted by the site owner.
    Rakuten prohibits rewriting link attributes or extracting/shortening href.
    Never execute, interpolate or reserialize arbitrary supplied HTML.
    """
    entry = guide.get("affiliate")
    if entry is None:
        return ""
    if (entry.get("provider") != "rakuten_travel"
            or entry.get("type") != "manually_generated_html"
            or entry.get("site_registered") is not True
            or entry.get("registered_site_url") != "https://harima-yorimichi.pages.dev/"):
        raise GuideError("広告リンクの掲載先登録または発行元を確認できません")
    original = entry.get("source_html")
    if not isinstance(original, str):
        raise GuideError("楽天が発行したHTMLソースがありません")
    anchor = re.fullmatch(
        r'<a href="(?P<href>https://[^"<>\s]+)" target="_blank" '
        r'rel="nofollow sponsored noopener" style="word-wrap:break-word;">'
        r'(?P<text>https://[^<>"]+)</a>',
        original,
    )
    if anchor is None:
        raise GuideError("楽天テキストリンクのHTMLソースに変更があります")
    href, label = anchor.group("href"), anchor.group("text")
    safe_url(href)
    parts = urlsplit(href)
    if parts.hostname != "hb.afl.rakuten.co.jp" or not parts.path.startswith("/hgc/"):
        raise GuideError("楽天アフィリエイト発行URLを確認できません")
    query = parse_qs(parts.query, keep_blank_values=True)
    if set(query) != {"pc", "link_type", "ut"} or query.get("link_type") != ["text"]:
        raise GuideError("楽天のテキストリンク用パラメータが不正です")
    destination = entry.get("destination_url")
    if not isinstance(destination, str):
        raise GuideError("広告リンクの遷移先情報がありません")
    safe_url(destination)
    target = urlsplit(destination)
    if target.hostname != "travel.rakuten.co.jp" or not target.path.startswith("/yado/"):
        raise GuideError("楽天トラベルの宿泊施設一覧ではありません")
    if query["pc"] != [destination] or label != destination or not query["ut"][0]:
        raise GuideError("楽天が発行したリンク先・テキストと記録が一致しません")
    return original



def travel_filename(guide):
    return "trip-" + guide["id"] + ".html"


def reviewed_guides(raw, now):
    """Historical preview dates omit later editorials rather than inventing them."""
    if raw.get("schema_version") != 1:
        raise GuideError("旅行ガイドの版が不正です")
    ids = set()
    visible = []
    for guide in raw["items"]:
        if guide["id"] in ids:
            raise GuideError("旅行ガイドIDが重複しています")
        ids.add(guide["id"])
        reviewed = parse_time(guide["last_reviewed_at"])
        if reviewed > now:
            continue
        urls = set()
        for day in guide["days"]:
            for stop in day["stops"]:
                url = safe_url(stop["official_url"])
                urls.add(url)
        if len(urls) < 3:
            raise GuideError("旅行ガイドに独立した公式確認先が3件必要です")
        for value in (guide["title"], guide["summary"], guide["origin"], guide["lodging_note"],
                      *guide["planning_notes"]):
            if any(ch in value for ch in "<>\r\n"):
                raise GuideError("旅行ガイドにHTML・改行を含めないでください")
        approved_affiliate_html(guide)
        visible.append(guide)
    return visible


def search_eligible(guide, now):
    """Manual approval is independent of general event/venue SEO thresholds."""
    age = now - parse_time(guide["last_reviewed_at"])
    return guide["review_status"] == "approved" and timedelta(0) <= age <= MAX_SEO_REVIEW_AGE


def guide_card(guide):
    heading = escape(guide["title"], quote=True)
    status = "記事確認中" if guide["review_status"] == "preview" else "確認済みのモデルコース"
    promo = bool(approved_affiliate_html(guide))
    notice = ("公式施設情報をもとに作成。個別宿泊施設の比較は準備中で、記事には広告・PRリンクを含みます。"
              if promo else "公式施設情報をもとに作成。宿泊比較・広告リンクは準備中です。")
    return ('<article class="card"><span class="tag">' + escape(status) + '</span>'
            '<h3><a href="' + travel_filename(guide) + '">' + heading + '</a></h3>'
            '<p>' + escape(guide["summary"]) + '</p>'
            '<p class="muted">' + escape(notice) + '</p></article>')


def guide_body(guide):
    affiliate_markup = approved_affiliate_html(guide)
    status = ("公開前確認中のモデルコースです。個別宿泊施設の料金・定員は未確認です。"
              if affiliate_markup and guide["review_status"] == "preview"
              else "公開前確認中のモデルコースです。宿泊施設の紹介と楽天トラベル広告は準備中です。"
              if guide["review_status"] == "preview"
              else "訪問先の最新の営業日・料金・参加条件は各施設の公式案内で確認してください。")
    ad_notice = ('<p class="ad-notice">広告・PR：この記事には楽天トラベルの'
                 'アフィリエイトリンクを掲載しています。</p>' if affiliate_markup else '')
    parts = [
        '<section class="intro"><p class="eyebrow">播磨から出かける、家族旅行のアイデア</p>',
        ad_notice,
        '<p>' + escape(guide["summary"]) + '</p>',
        '<p class="muted">' + escape(guide["origin"]) + '</p></section>',
        '<section class="notice"><h2>掲載状況</h2><p>' + escape(status) + '</p></section>',
        '<h2>2日間の回り方案</h2>',
        '<p>移動時間・滞在時間は旅行日によって変わるため固定していません。'
        '公園や施設の利用条件を確認し、無理のない順番に入れ替えてください。</p>',
    ]
    for day in guide["days"]:
        parts.append('<section><h2>' + escape(day["title"]) + '</h2><div class="cards">')
        for stop in day["stops"]:
            parts.extend([
                '<article class="card"><h3>' + escape(stop["name"]) + '</h3>',
                '<p>' + escape(stop["description"]) + '</p>',
                '<p><a href="' + escape(stop["official_url"], quote=True) +
                '" rel="noopener noreferrer">公式サイトで最新情報を見る</a></p></article>',
            ])
        parts.append('</div></section>')
    if affiliate_markup:
        parts.extend([
            '<section class="notice" aria-label="楽天トラベルの広告">',
            '<h2>淡路島の宿泊施設を探す（広告・PR）</h2>',
            '<p>' + escape(guide["lodging_note"]) + '</p>',
            '<p>次のリンクは楽天トラベルの淡路島エリア宿泊施設一覧へ移動します。'
            '特定の宿泊先の空室・料金・定員を保証するものではありません。</p>',
            '<p class="travel-booking-reference">' + affiliate_markup + '</p>',
            '<p class="muted">広告リンクが表示されない場合は、'
            '<a href="' + escape(guide["affiliate"]["destination_url"], quote=True) +
            '" rel="noopener noreferrer">楽天トラベルの淡路島エリア宿泊施設一覧（通常リンク）</a>'
            'をご利用ください。この通常リンクにはアフィリエイト報酬は発生しません。</p>',
            '<p class="muted">広告リンク経由の予約等により、サイト運営者に'
            '成果報酬が発生する場合があります。</p></section>',
        ])
    else:
        parts.extend([
            '<section class="notice"><h2>宿泊・楽天トラベルの比較は準備中</h2>',
            '<p>' + escape(guide["lodging_note"]) + '</p></section>',
        ])
    parts.append('<section><h2>家族旅行の予約前チェック</h2><ul>')
    for note in guide["planning_notes"]:
        parts.append('<li>' + escape(note) + '</li>')
    parts.extend([
        '</ul></section>',
        '<p class="muted">掲載した施設情報の確認日：' +
        escape(parse_time(guide["last_reviewed_at"]).date().isoformat()) +
        '。写真・レビュー・第三者記事本文は転載していません。</p>',
    ])
    return "".join(parts)
