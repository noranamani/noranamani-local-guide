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


def approved_picttext_html(guide, entry, original):
    """Validate a fixed-format Rakuten-issued image+text ad; never reserialize it."""
    start = ('<table border="0" cellpadding="0" cellspacing="0"><tr><td>'
             '<div style="border:1px solid #95a5a6;border-radius:.75rem;'
             'background-color:#FFFFFF;margin:0px;padding:5px;text-align:center;overflow:hidden;">'
             '<table><tr><td style="width:100px"><a href="')
    before_image = ('" target="_blank" rel="nofollow sponsored noopener" '
                    'style="word-wrap:break-word;"><img src="')
    between_links = ('" border="0" style="margin:2px" alt="" title=""></a></td>'
                     '<td style="vertical-align:top;display: block;">'
                     '<p style="font-size:12px;line-height:1.4em;text-align:left;margin:0px;'
                     'padding:2px 6px;word-wrap:break-word"><a href="')
    before_label = ('" target="_blank" rel="nofollow sponsored noopener" '
                    'style="word-wrap:break-word;">')
    ending = ('</a></p></td></tr></table></div><br>'
              '<p style="color:#000000;font-size:12px;line-height:1.4em;margin:5px;'
              'word-wrap:break-word"></p></td></tr></table>')
    pattern = (re.escape(start) + r'(?P<href>https://[^"<>\s]+)'
               + re.escape(before_image) + r'(?P<img>https://[^"<>\s]+)'
               + re.escape(between_links) + r'(?P=href)' + re.escape(before_label)
               + r'(?P<label>[^<>&]{2,80})' + re.escape(ending))
    match = re.fullmatch(pattern, original)
    if match is None or match.group("label") != guide.get("lodging_name"):
        raise GuideError("楽天の画像付き広告HTMLが公式発行形式と一致しません")
    href, image_url = match.group("href"), match.group("img")
    safe_url(href)
    safe_url(image_url)
    affiliate_parts, image_parts = urlsplit(href), urlsplit(image_url)
    destination = entry.get("destination_url")
    safe_url(destination)
    hotel_parts = urlsplit(destination)
    hotel_match = re.fullmatch(r"/HOTEL/([0-9]+)/\1\.html", hotel_parts.path)
    if not (hotel_parts.hostname == "travel.rakuten.co.jp" and hotel_match
            and affiliate_parts.hostname == "hb.afl.rakuten.co.jp"
            and affiliate_parts.path.startswith("/hgc/")
            and image_parts.hostname == "hbb.afl.rakuten.co.jp"
            and image_parts.path.startswith("/hgb/")):
        raise GuideError("楽天広告の発行元または宿泊施設URLが不正です")
    link_query = parse_qs(affiliate_parts.query, keep_blank_values=True)
    image_query = parse_qs(image_parts.query, keep_blank_values=True)
    if (set(link_query) != {"pc", "link_type", "ut"}
            or link_query["pc"] != [destination]
            or link_query["link_type"] != ["picttext"]
            or not link_query["ut"][0]
            or set(image_query) != {"me_id", "item_id", "pc"}
            or not image_query["me_id"][0].isdigit()
            or image_query["item_id"] != [hotel_match.group(1)]):
        raise GuideError("楽天広告のトラッキング先と施設情報が一致しません")
    image_target = image_query["pc"][0]
    safe_url(image_target)
    image_target_parts = urlsplit(image_target)
    if (image_target_parts.hostname != "img.travel.rakuten.co.jp"
            or image_target_parts.path != "/image/imgr_100"
            or parse_qs(image_target_parts.query) != {"no": [hotel_match.group(1)]}):
        raise GuideError("楽天広告の画像URLが施設と一致しません")
    return original



def approved_affiliate_html(guide):
    """Accept only an unaltered manually issued Rakuten affiliate snippet.

    Text-link attributes remain byte-for-byte as submitted by the site owner.
    Rakuten prohibits rewriting link attributes or extracting/shortening href.
    Never execute, interpolate or reserialize arbitrary supplied HTML.
    """
    entry = guide.get("affiliate")
    if entry is None:
        return ""
    if (entry.get("provider") != "rakuten_travel"
            or entry.get("type") not in ("manually_generated_html", "manually_generated_picttext_html")
            or entry.get("site_registered") is not True
            or entry.get("registered_site_url") != "https://harima-yorimichi.pages.dev/"):
        raise GuideError("広告リンクの掲載先登録または発行元を確認できません")
    original = entry.get("source_html")
    if not isinstance(original, str):
        raise GuideError("楽天が発行したHTMLソースがありません")
    if entry["type"] == "manually_generated_picttext_html":
        return approved_picttext_html(guide, entry, original)
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
                      guide.get("lodging_name", ""), *guide["planning_notes"]):
            if any(ch in value for ch in "<>\r\n"):
                raise GuideError("旅行ガイドにHTML・改行を含めないでください")
        approved_affiliate_html(guide)
        visible.append(guide)
    return visible


def search_eligible(guide, now):
    """Manual approval is independent of general event/venue SEO thresholds."""
    age = now - parse_time(guide["last_reviewed_at"])
    return guide["review_status"] == "approved" and timedelta(0) <= age <= MAX_SEO_REVIEW_AGE


def guide_card(guide, compact=False):
    """Show concise destinations; preserve full article names for screen readers."""
    full_title = escape(guide["title"], quote=True)
    is_actual = guide.get("trip_basis") == "actual_trip"
    status = ("旅行記（記事確認中）" if is_actual and guide["review_status"] == "preview"
              else "記事確認中" if guide["review_status"] == "preview"
              else "確認済みのモデルコース")
    promo = bool(approved_affiliate_html(guide))
    notice = ("実際の家族旅行をもとにした訪問ルートです。宿泊施設への広告・PRリンクがあります。"
              if is_actual and promo
              else "公式施設情報をもとに作成。個別宿泊施設の比較は準備中で、記事には広告・PRリンクを含みます。"
              if promo else "公式施設情報をもとに作成。宿泊比較・広告リンクは準備中です。")
    # Card-only copy derived from each existing article, not a change to article data.
    presets = {
        "awaji-family-one-night": (
            "淡路島1泊2日", "淡路島の旅",
            "花畑や公園・体験施設をめぐる、家族向けモデルコース。"
        ),
        "sanin-family-one-night": (
            "山陰1泊2日", "山陰の旅",
            "水木しげるロードから出雲・鳥取砂丘へ。実際に巡った家族旅の記録。"
        ),
    }
    label, scenic_label, short_summary = presets.get(
        guide["id"], (guide["title"], "家族旅行", guide["summary"])
    )
    artwork_class = ("trip-card__visual trip-card__visual--awaji"
                     if guide["id"] == "awaji-family-one-night"
                     else "trip-card__visual trip-card__visual--sanin"
                     if guide["id"] == "sanin-family-one-night" else "trip-card__visual")
    illustration_note = ("※画像はイメージです" if guide["id"] == "awaji-family-one-night"
                         else "※背景は装飾イメージです")
    kind = "実際の旅行記" if is_actual else "モデルコース"
    summary = short_summary if compact else guide["summary"]
    notice_on_card = ("広告・PRリンクあり" if promo else "公式情報の確認はこちら") if compact else notice
    card_class = "card trip-card trip-card--compact" if compact else "card trip-card"
    return ('<article class="' + card_class + '">'
            '<a class="trip-card__link" href="' + travel_filename(guide) +
            '" aria-label="' + full_title + 'を読む">'
            '<div class="' + artwork_class + '" aria-hidden="true">'
            '<span class="trip-card__visual-label">' + escape(scenic_label) + '</span>'
            '<span class="trip-card__visual-note">' + escape(illustration_note) + '</span></div>'
            '<div class="trip-card__content"><div class="trip-card__badges">'
            '<span class="tag">' + escape(status) + '</span>'
            '<span class="trip-card__kind">' + escape(kind) + '</span></div>'
            '<h3>' + escape(label) + '</h3>'
            '<p class="trip-card__summary">' + escape(summary) + '</p>'
            '<p class="muted trip-card__notice">' + escape(notice_on_card) + '</p>'
            '<span class="trip-card__foot" aria-hidden="true">プランを読む →</span>'
            '</div></a></article>')


def guide_body(guide):
    affiliate_markup = approved_affiliate_html(guide)
    is_actual = guide.get("trip_basis") == "actual_trip"
    picttext = (guide.get("affiliate") or {}).get("type") == "manually_generated_picttext_html"
    status = ("2026年の家族旅行で訪れた順番をもとにした記録です。最新の営業時間・料金は各公式案内をご確認ください。"
              if is_actual
              else "公開前確認中のモデルコースです。個別宿泊施設の料金・定員は未確認です."
              if affiliate_markup and guide["review_status"] == "preview"
              else "公開前確認中のモデルコースです。宿泊施設の紹介と楽天トラベル広告は準備中です。"
              if guide["review_status"] == "preview"
              else "訪問先の最新の営業日・料金・参加条件は各施設の公式案内で確認してください。")
    ad_notice = ('<p class="ad-notice">広告・PR：この記事には楽天トラベルの'
                 'アフィリエイトリンクを掲載しています。</p>' if affiliate_markup else '')
    if guide["id"] == "awaji-family-one-night":
        article_cover = (
            '<div class="article-cover article-cover--awaji">'
            '<h1>' + escape(guide["title"]) + '</h1>'
            '<span class="article-cover__note">※画像はイメージです</span></div>'
        )
    elif guide["id"] == "sanin-family-one-night":
        article_cover = (
            '<div class="article-cover article-cover--sanin">'
            '<h1>' + escape(guide["title"]) + '</h1>'
            '<span class="article-cover__note">※背景は装飾イメージです</span></div>'
        )
    else:
        article_cover = '<div class="article-cover" aria-hidden="true"></div>'
    jumps = ('<nav class="article-jump" aria-label="日程別に移動">' +
             "".join('<a href="#day-' + str(i) + '">' + str(i) + '日目の行程を見る →</a>'
                     for i in range(1, len(guide["days"]) + 1)) + '</nav>')
    parts = [
        '<nav class="breadcrumbs" aria-label="現在位置">'
        '<a href="index.html">ホーム</a><span aria-hidden="true">›</span>'
        '<a href="travel.html">家族旅行</a><span aria-hidden="true">›</span>'
        '<span>旅行記事</span></nav>',
        article_cover,
        '<section class="intro"><p class="eyebrow">' +
        ("実際に訪れた家族旅行の記録" if is_actual
         else "播磨から出かける、家族旅行のアイデア") + '</p>',
        ad_notice,
        '<p>' + escape(guide["summary"]) + '</p>',
        '<p class="muted">' + escape(guide["origin"]) + '</p></section>',
        '<section class="notice"><h2>掲載状況</h2><p>' + escape(status) + '</p></section>',
        '<h2>' + ("1泊2日の訪問ルート" if is_actual else "2日間の回り方案") + '</h2>',
        ('<p>以下は実際の訪問順です。営業時間・移動時間・宿泊条件は現在と異なるため、'
         '同じ旅程を組む場合は公式情報を確認し、無理のない日程に調整してください。</p>'
         if is_actual else
         '<p>移動時間・滞在時間は旅行日によって変わるため固定していません。'
         '公園や施設の利用条件を確認し、無理のない順番に入れ替えてください。</p>'),
        jumps,
    ]
    for day_index, day in enumerate(guide["days"], start=1):
        parts.append('<section class="route-day" id="day-' + str(day_index) + '">'
                     '<div class="route-day__heading">'
                     '<span class="route-day__badge">DAY ' + str(day_index).zfill(2) + '</span>'
                     '<h2>' + escape(day["title"]) + '</h2></div>'
                     '<div class="route-steps">')
        for stop_index, stop in enumerate(day["stops"], start=1):
            parts.extend([
                '<article class="route-step">'
                '<span class="route-step__pin" aria-hidden="true">' + str(stop_index) + '</span>'
                '<h3>' + escape(stop["name"]) + '</h3>',
                '<p>' + escape(stop["description"]) + '</p>',
                '<a class="route-step__official" href="' + escape(stop["official_url"], quote=True) +
                '" rel="noopener noreferrer">公式サイトで最新情報を見る ↗</a></article>',
            ])
        parts.append('</div></section>')
    if affiliate_markup:
        ad_heading = ("松江市宍道ふるさと森林公園の宿泊予約（広告・PR）"
                      if picttext else "淡路島の宿泊施設を探す（広告・PR）")
        ad_explanation = ("次の広告リンクは楽天トラベルの当該宿泊施設のページへ移動します。"
                          "空室・料金・定員・宿泊内容を保証するものではありません。"
                          if picttext else
                          "次のリンクは楽天トラベルの淡路島エリア宿泊施設一覧へ移動します。"
                          "特定の宿泊先の空室・料金・定員を保証するものではありません。")
        fallback_label = ("楽天トラベルで松江市宍道ふるさと森林公園を見る（通常リンク）"
                          if picttext else "楽天トラベルの淡路島エリア宿泊施設一覧（通常リンク）")
        fallback_notice = ("リンク先で最新の情報をご確認ください。"
                           if picttext else "この通常リンクにはアフィリエイト報酬は発生しません。")
        ad_markup = ('<div class="travel-booking-reference travel-booking-reference--picttext">'
                     + affiliate_markup + '</div>' if picttext else
                     '<p class="travel-booking-reference">' + affiliate_markup + '</p>')
        parts.extend([
            '<section class="notice" aria-label="楽天トラベルの広告">',
            '<h2>' + escape(ad_heading) + '</h2>',
            '<p>' + escape(guide["lodging_note"]) + '</p>',
            '<p>' + escape(ad_explanation) + '</p>',
            ad_markup,
            '<p class="muted">広告リンクが表示されない場合は、'
            '<a href="' + escape(guide["affiliate"]["destination_url"], quote=True) +
            '" rel="noopener noreferrer">' + escape(fallback_label) + '</a>'
            'をご利用ください。' + fallback_notice + '</p>',
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
        ('。この記事の訪問順は実際の家族旅行をもとにしています。'
         '施設の写真・第三者記事本文は転載していません。</p>'
         if is_actual else
         '。写真・レビュー・第三者記事本文は転載していません。</p>'),
    ])
    parts.append('<p class="article-back"><a href="travel.html">← 家族旅行の一覧に戻る</a></p>')
    return "".join(parts)
