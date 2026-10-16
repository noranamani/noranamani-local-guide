"""Human-reviewed family travel guide pages; never fetch ads or external content.

Each listed attraction links to its primary/official source. Guides are visibly
marked as preparation drafts until editorial approval, and affiliate links are
deliberately unavailable until site registration and compliance review.
"""
from datetime import timedelta
from html import escape

from .core import GuideError, parse_time, safe_url

MAX_SEO_REVIEW_AGE = timedelta(days=90)


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
        visible.append(guide)
    return visible


def search_eligible(guide, now):
    """Manual approval is independent of general event/venue SEO thresholds."""
    age = now - parse_time(guide["last_reviewed_at"])
    return guide["review_status"] == "approved" and timedelta(0) <= age <= MAX_SEO_REVIEW_AGE


def guide_card(guide):
    heading = escape(guide["title"], quote=True)
    status = "記事確認中" if guide["review_status"] == "preview" else "確認済みのモデルコース"
    return ('<article class="card"><span class="tag">' + escape(status) + '</span>'
            '<h3><a href="' + travel_filename(guide) + '">' + heading + '</a></h3>'
            '<p>' + escape(guide["summary"]) + '</p>'
            '<p class="muted">公式施設情報をもとに作成。宿泊比較・広告リンクは準備中です。</p></article>')


def guide_body(guide):
    status = ("公開前確認中のモデルコースです。宿泊施設の紹介と楽天トラベル広告は準備中です。"
              if guide["review_status"] == "preview"
              else "訪問先の最新の営業日・料金・参加条件は各施設の公式案内で確認してください。")
    parts = [
        '<section class="intro"><p class="eyebrow">播磨から出かける、家族旅行のアイデア</p>',
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
    parts.extend([
        '<section class="notice"><h2>宿泊・楽天トラベルの比較は準備中</h2>',
        '<p>' + escape(guide["lodging_note"]) + '</p></section>',
        '<section><h2>家族旅行の予約前チェック</h2><ul>',
    ])
    for note in guide["planning_notes"]:
        parts.append('<li>' + escape(note) + '</li>')
    parts.extend([
        '</ul></section>',
        '<p class="muted">掲載した施設情報の確認日：' +
        escape(parse_time(guide["last_reviewed_at"]).date().isoformat()) +
        '。写真・レビュー・第三者記事本文は転載していません。</p>',
    ])
    return "".join(parts)
