"""Generate and validate a static Japanese site before replacing the last good output."""
import html
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .core import GuideError, active_occurrences, atomic_json, read_json, safe_url, serialized
from .normalize import identifier
from .page_places import qualified_places, sustained_listing
from .validation import inspect_text, publishable, validate_data, validate_config
from .travel_guides import reviewed_guides, travel_filename, guide_card, guide_body, search_eligible

STYLE = """:root {
  color-scheme: light;
  --ink: #203a34;
  --muted: #526a61;
  --bg: #f7f8f4;
  --paper: #ffffff;
  --brand: #096858;
  --border: #dce7df;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; min-height: 100vh; background: var(--bg); color: var(--ink); font: 16px/1.75 system-ui, -apple-system, "Noto Sans JP", sans-serif; }
a { color: var(--brand); text-underline-offset: .2em; }
a:hover { text-decoration-thickness: .13em; }
a:focus-visible, summary:focus-visible { outline: 3px solid #a35f0b; outline-offset: 4px; }
.skip-link { position: absolute; top: -6rem; left: 1rem; z-index: 20; padding: .6rem 1rem; background: var(--paper); }
.skip-link:focus { top: .6rem; }
.site-header { background: linear-gradient(110deg, #e9f3ec, #fff9ec); border-bottom: 1px solid var(--border); }
.site-header__inner, main, .site-footer__inner { max-width: 1040px; margin: 0 auto; padding: 1.5rem clamp(1rem, 4vw, 2.5rem); }
.brand { display: inline-block; color: var(--ink); font-size: clamp(1.4rem, 4vw, 1.9rem); font-weight: 800; letter-spacing: .02em; text-decoration: none; }
.brand:hover { text-decoration: underline; }
.tagline { margin: .2rem 0 1rem; color: var(--muted); font-size: .96rem; }
nav { display: flex; flex-wrap: wrap; gap: .5rem; }
nav a { display: inline-flex; padding: .35rem .8rem; border: 1px solid #c9ded1; border-radius: 999px; background: #fffdf9; font-weight: 650; text-decoration: none; }
nav a:hover { background: #f0f9f3; }
main { padding-top: 2rem; padding-bottom: 3rem; }
h1 { margin: 0 0 1.3rem; font-size: clamp(1.7rem, 4.8vw, 2.45rem); line-height: 1.45; letter-spacing: .01em; }
h2 { margin: 1.7rem 0 .7rem; font-size: 1.3rem; line-height: 1.5; }
h3 { margin: .2rem 0 .6rem; font-size: 1.12rem; line-height: 1.5; }
p { margin: .65rem 0; }
.intro { padding: clamp(1rem, 3vw, 1.6rem); margin-bottom: 1.6rem; background: #eaf3ee; border: 1px solid #d6e9df; border-radius: 18px; }
.intro p { max-width: 68ch; }
.eyebrow { margin: 0; color: #2c6855; font-size: .88rem; font-weight: 800; letter-spacing: .08em; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr)); gap: 1rem; align-items: start; }
.card, .notice { background: var(--paper); border: 1px solid var(--border); border-radius: 16px; padding: clamp(1rem, 2.5vw, 1.45rem); margin: .65rem 0; box-shadow: 0 2px 10px rgb(16 54 39 / 4%); }
.card h2, .card h3 { margin-top: 0; }
.card dl { display: grid; grid-template-columns: minmax(5em, 7em) 1fr; column-gap: .6rem; row-gap: .25rem; margin: .8rem 0; }
.card dt { font-weight: 750; }
.card dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.notice { border-left: 4px solid #80a994; }
.notice h2 { margin-top: 0; }
.muted, .source-credit { color: var(--muted); font-size: .88rem; }
.source-credit { border-top: 1px solid var(--border); margin-top: 1rem; padding-top: .7rem; }
.source-details { margin-top: .6rem; font-size: .88rem; }
.source-details summary { color: var(--brand); cursor: pointer; font-weight: 700; }
.source-details ul { padding-left: 1.15rem; overflow-wrap: anywhere; }
.source-details li + li { margin-top: .65rem; }
.ad-notice { font-weight: 800; padding: .45rem .75rem; margin: .65rem 0; background: #fff9e8; border: 1px solid #dfc995; border-radius: 8px; }
.affiliate-link { margin: 1.1rem 0; padding: .65rem; overflow-wrap: anywhere; border: 1px solid var(--border); border-radius: 8px; }
.tag { display: inline-block; padding: .1rem .55rem; background: #edf4e9; border-radius: 999px; color: #315642; font-size: .85rem; }
ul { padding-left: 1.3rem; }
.site-footer { border-top: 1px solid var(--border); background: #eef2ec; color: var(--muted); font-size: .88rem; }
.site-footer__inner { padding-top: 1.15rem; padding-bottom: 1.15rem; }
@media (max-width: 600px) {
  main { padding-top: 1.5rem; }
  nav a { font-size: .94rem; }
  .card dl { grid-template-columns: 1fr; row-gap: 0; }
  .card dd { margin-bottom: .45rem; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
"""


# Cloudflare Pages uses docs/_headers when serving static assets. Defense in
# depth: the HTTP header blocks indexing if no individual HTML is indexable.
def cloudflare_headers(block_indexing):
    result = (
        "/*\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
    )
    if block_indexing:
        result += "  X-Robots-Tag: noindex\n"
    return result


SITE_NAME = "はりまよりみち"
SITE_TAGLINE = "加古川・明石・姫路と周辺のイベント・お店・おでかけ情報"


def escaped(value):
    return html.escape(str(value), quote=True)


def event_file(event):
    return f"event-{identifier(event['event_id'])}.html"


def date_label(value):
    if value is None:
        return "不明"
    return value.replace("T", " ").replace("+09:00", "（日本時間）")


def page(title, description, body, filename, site_url, indexable, nav):
    canonical = f'<link rel="canonical" href="{escaped(site_url.rstrip("/") + "/" + filename)}">' if site_url and indexable else ""
    robots = "index,follow" if site_url and indexable else "noindex,follow"
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escaped(title)} | {escaped(SITE_NAME)}</title><meta name="description" content="{escaped(description)}">
<meta name="robots" content="{robots}">{canonical}<link rel="stylesheet" href="styles.css"></head>
<body><a class="skip-link" href="#main-content">本文へ移動</a>
<header class="site-header"><div class="site-header__inner">
<a class="brand" href="index.html">{escaped(SITE_NAME)}</a><p class="tagline">{escaped(SITE_TAGLINE)}</p>
<nav aria-label="主なページ">{nav}</nav></div></header>
<main id="main-content"><h1>{escaped(title)}</h1>{body}</main>
<footer class="site-footer"><div class="site-footer__inner">
<p>日程・料金・参加条件は変更される場合があります。お出かけ前に公式情報をご確認ください。</p>
<p>確認できない情報は「不明」と表示します。掲載内容は確認済みの事実情報から構成しています。</p>
</div></footer></body></html>'''



def source_links(record, sources):
    ranked = sorted(record["sources"], key=lambda p: (not p["is_primary"], p["source_id"]))
    entries = []
    for provenance in ranked:
        source = sources[provenance["source_id"]]
        publication = date_label(provenance["source_published_at"])
        entries.append(f'<li data-source-id="{escaped(source["id"])}" data-verified-at="{escaped(provenance["last_checked_at"])}"><a href="{escaped(provenance["url"])}" rel="noopener noreferrer">{escaped(source["label"])}（公式・情報源）</a>'
                       f'<br>取得日時：{escaped(date_label(provenance["fetched_at"]))} / 最終確認：{escaped(date_label(provenance["last_checked_at"]))}'
                       f'<br>発表日時：{escaped(publication)} / <a href="{escaped(source["permission_document"])}" rel="noopener noreferrer">利用条件・出典</a></li>')
        if source.get("attribution_url"):
            entries.append(f'<li><a href="{escaped(source["attribution_url"])}" rel="noopener noreferrer">出典：{escaped(source["label"])} 配布ページ</a>'
                           f'<br>{escaped(source.get("adaptation_notice", "出典の事実情報を整理して作成しました。"))}</li>')
    credits = []
    for provenance in ranked:
        source = sources[provenance["source_id"]]
        credit_url = source.get("attribution_url") or provenance["url"]
        credits.append(f'<a href="{escaped(credit_url)}" rel="noopener noreferrer">{escaped(source["label"])}</a>')
    return ('<p class="source-credit">出典：' + "、".join(credits) + '</p>'
            + '<details class="source-details"><summary>出典・確認履歴の詳細</summary>'
            + '<ul class="muted">' + "".join(entries) + '</ul></details>')


def event_content(event, sources, now, detail=False):
    occurrences = active_occurrences(event, now)
    dates = "".join(f'<li>{escaped(date_label(o["start_at"]))} 〜 {escaped(date_label(o["end_at"]))}</li>' for o in occurrences)
    price = {"free": "無料（条件は公式情報で確認）", "paid": "有料", "conditional": "条件付き", "unknown": "不明"}[event["price_type"]]
    indoor = {"indoor": "屋内", "outdoor": "屋外", "mixed": "屋内・屋外", "unknown": "不明"}[event["indoor_outdoor"]]
    title = escaped(event["title"])
    heading = title if detail else f'<a href="{event_file(event)}">{title}</a>'
    reservation = {True: "必要", False: "不要", None: "不明"}[event["reservation_required"]]
    official = f'<p><a href="{escaped(event["official_url"])}" rel="noopener noreferrer">公式の開催情報</a></p>' if event.get("official_url") else ""
    return (f'<article class="card"><h2>{heading}</h2><span class="tag">{escaped(event["municipality"])}</span>'
            f'<h3>確認済みの開催回</h3><ul>{dates}</ul><dl><dt>会場</dt><dd>{escaped(event["location_label"] or "不明")}</dd>'
            f'<dt>料金</dt><dd>{escaped(price)} / {escaped(event["price_description"] or "詳細不明")}</dd>'
            f'<dt>対象年齢</dt><dd>{escaped(event["age_info"] or "不明")}</dd><dt>屋内・屋外</dt><dd>{indoor}</dd>'
            f'<dt>予約</dt><dd>{reservation}</dd><dt>最終確認</dt><dd>{escaped(date_label(event["last_verified_at"]))}</dd></dl>'
            '<p>お出かけ前に公式情報で開催状況と参加条件をご確認ください。</p>' + official + source_links(event, sources) + '</article>')


def place_content(place, sources):
    """Render public facility facts and source attribution; no inferred ratings."""
    address = escaped(place["address"] or "住所不明")
    admission = escaped(place["admission"] or "不明")
    return (f'<article class="card"><h3>{escaped(place["name"])}</h3>'
            f'<p>{escaped(place["municipality"])} / {address}</p>'
            f'<p>料金：{admission}</p>'
            f'<a href="{escaped(place["official_url"])}" rel="noopener noreferrer">公式情報</a>'
            + source_links(place, sources) + '</article>')


def qualified(events, rules):
    minimum = rules["list_pages"]
    return (len(events) >= minimum["min_active_items"]
            and sum(any(s["is_primary"] for s in e["sources"]) for e in events) >= minimum["min_official_items"]
            and len({e.get("organizer_label") for e in events if e.get("organizer_label")}) >= minimum["min_distinct_organizers"])


def create_files(root, now):
    data = validate_data(root, now)
    areas, categories, rules, config = validate_config(root, now)
    sources = {s["id"]: s for s in config["sources"]}
    stale = rules["review"]["stale_event_after_hours"]
    events = [e for e in data["events"]["items"] if active_occurrences(e, now) and publishable(e, sources, now, stale)]
    events.sort(key=lambda e: (active_occurrences(e, now)[0]["start_at"], e["event_id"]))
    places = [p for p in data["places"]["items"] if publishable(p, sources, now, stale)]
    travel_guides = reviewed_guides(data.get("travel_guides", {"schema_version": 1, "items": []}), now)
    state_path = root / "cache/page_state.json"
    page_state = read_json(state_path) if state_path.exists() else {}
    groups = {}
    for area in areas["areas"]:
        groups[f'area-{area["id"]}.html'] = (area["name"] + "の開催情報", [e for e in events if e["municipality"] in (area["id"], area["name"])])
    for category in categories["primary"]:
        if category["id"] != "trip":
            groups[f'category-{category["id"]}.html'] = (category["label"] + "の開催情報", [e for e in events if category["id"] in e["category_ids"]])
    ready = {}
    for filename, (title, items) in groups.items():
        if sustained_listing(filename, qualified(items, rules), page_state, now,
                             rules["list_pages"]["activate_after_days"]):
            ready[filename] = (title, items)

    # Place listings do not depend on organizer_label or event availability.
    places_ready = sustained_listing("places.html",
                                    qualified_places(places, rules["place_pages"]),
                                    page_state, now, rules["place_pages"]["activate_after_days"])
    nav = ('<a href="index.html">ホーム</a>'
           + ('<a href="events.html">開催情報一覧</a>' if events else '')
           + ('<a href="places.html">施設一覧</a>' if places else '')
           + ('<a href="travel.html">家族旅行</a>' if travel_guides else ''))
    files, indexable_files = {"styles.css": STYLE}, []
    url = rules["site_url"]

    def add(filename, title, description, body, indexable):
        files[filename] = page(title, description, body, filename, url, indexable, nav)
        if indexable and url:
            indexable_files.append(filename)

    cards = "".join(event_content(e, sources, now) for e in events)
    place_cards = "".join(place_content(p, sources) for p in places)
    intro = ('<section class="intro" aria-label="サイト案内">'
             '<p class="eyebrow">播磨のおでかけを、確かな情報から。</p>'
             '<p>加古川・明石・姫路と周辺の施設やイベントを、公式情報と出典に基づいて整理する地域ガイドです。</p>'
             '<p class="muted">料金や開催条件が確認できない場合、推測して掲載することはありません。</p>'
             '</section>')
    cards_notice = ('<section class="notice" aria-label="開催情報の準備状況">'
                    '<h2>イベント情報は準備中です</h2>'
                    '<p>現在、開催日時や会場を確認できるイベントは掲載していません。確認が取れたものから案内します。</p>'
                    '</section>')
    if not events and not places and not travel_guides:
        content = ('<section class="notice"><h2>掲載準備中です</h2>'
                   '<p>現在、公開できる確認済みの情報はありません。情報源の利用条件と掲載内容を確認してから掲載します。</p>'
                   '</section>')
    else:
        content = ('<h2>開催情報</h2><div class="cards">' + cards + '</div>') if events else cards_notice
        if places:
            content += '<h2>確認済みの施設</h2><div class="cards">' + place_cards + '</div>'
        if travel_guides:
            content += ('<h2>加古川発・家族旅行のモデルコース</h2>'
                        ('<p>観光の立ち寄り先をまとめています。個別宿泊施設の比較は準備中です。'
                         + ('旅行記事には広告・PRリンクが含まれます。</p>' if any(g.get("affiliate") for g in travel_guides)
                            else '広告リンクは準備中です。</p>'))
                        '<div class="cards">' + "".join(guide_card(g) for g in travel_guides) + '</div>')
    content = intro + content
    travel_indexable = any(search_eligible(g, now) for g in travel_guides)
    add("index.html", "家族で出かける地域ガイド", "加古川・明石・姫路周辺の確認済み開催情報と施設案内、播磨からの家族旅行モデルコース。公式情報と確認日時を表示します。", content, qualified(events, rules) or places_ready or travel_indexable)
    if travel_guides:
        listing = ('<p>加古川方面から車で出かける、家族旅行の立ち寄り先を紹介します。'
                   '訪問順序は例示であり、営業時間・料金は各施設で確認してください。</p>'
                   '<div class="cards">' + "".join(guide_card(g) for g in travel_guides) + '</div>')
        add("travel.html", "加古川発・家族旅行プラン", "加古川から車で行ける1泊2日旅行のモデルコースと、宿泊予約前に確認したい条件のまとめです。", listing, travel_indexable)
        for guide in travel_guides:
            add(travel_filename(guide), guide["title"], guide["summary"], guide_body(guide), search_eligible(guide, now))
    if places:
        add("places.html", "確認済みの施設一覧", "加古川・明石・姫路周辺の施設名称、所在地と公式リンクを出典付きでまとめています。料金など不明な項目は推測しません。", '<div class="cards">' + place_cards + '</div>', places_ready)
    if events:
        add("events.html", "開催情報一覧", "確認済みの将来・開催中の開催回を掲載しています。終了・中止・未確認のイベントは掲載しません。", '<div class="cards">' + cards + '</div>', qualified(events, rules))
        for event in events:
            add(event_file(event), event["title"], f'{event["municipality"]}の開催情報。日程・会場・料金は公式情報をご確認ください。', event_content(event, sources, now, True), True)
    for filename, (title, items) in ready.items():
        add(filename, title, "公式情報・確認日時付きの地域開催情報。変更・中止については公式ページでご確認ください。", '<div class="cards">' + "".join(event_content(e, sources, now) for e in items) + '</div>', True)
    if url:
        files["robots.txt"] = "User-agent: *\n" + ("Allow: /\n" if indexable_files else "Disallow: /\n")
        if indexable_files:
            ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
            ET.register_namespace("", ns)
            tree = ET.Element(f"{{{ns}}}urlset")
            for filename in indexable_files:
                entry = ET.SubElement(tree, f"{{{ns}}}url")
                ET.SubElement(entry, f"{{{ns}}}loc").text = url.rstrip("/") + "/" + filename
            files["sitemap.xml"] = ET.tostring(tree, encoding="unicode", xml_declaration=True)
            files["robots.txt"] += "Sitemap: " + url.rstrip("/") + "/sitemap.xml\n"
    files["_headers"] = cloudflare_headers(not bool(indexable_files))
    files[".guide-manifest.json"] = json.dumps({"schema_version": 1, "generated_at": now.isoformat(),
                                               "files": sorted(files), "events": len(events), "places": len(places),
                                               "travel_guides": len(travel_guides)}, ensure_ascii=False, indent=2) + "\n"
    return files, page_state


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.title, self.headings = [], set(), [], []
        self.metas, self.canonical, self.lang, self.charset = {}, [], None, False
        self.capture = None
        self.stack = []
        self.errors = []
        self.provenance = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "data-source-id" in values:
            self.provenance.append(values)
        if tag in ("script", "iframe", "img", "form", "object", "embed", "base") or any(k.startswith("on") for k in values):
            self.errors.append("許可されない埋め込み要素・動的処理があります")
        if tag == "html":
            self.lang = values.get("lang")
        if tag == "meta":
            self.charset |= values.get("charset", "").lower() == "utf-8"
            if "name" in values:
                self.metas[values["name"]] = values.get("content", "")
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(values.get("href"))
        elif "href" in values:
            self.links.append(values["href"])
        if "id" in values:
            if values["id"] in self.ids:
                self.errors.append("HTML IDが重複しています")
            self.ids.add(values["id"])
        if tag in ("title", "h1"):
            self.capture = tag
        if tag not in ("meta", "link", "br", "hr", "input", "img", "source", "wbr", "area", "base", "embed"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.errors.append("HTML要素の対応が不正です")
        if tag == self.capture:
            self.capture = None

    def handle_data(self, data):
        if self.capture == "title":
            self.title.append(data)
        if self.capture == "h1":
            self.headings.append(data)


def validate_site(output, site_url=None):
    output = Path(output)
    manifest = read_json(output / ".guide-manifest.json")
    expected = set(manifest["files"]) | {".guide-manifest.json"}
    if not {"index.html", "styles.css"} <= expected:
        raise GuideError("必須のトップページまたはCSSがありません")
    if {p.name for p in output.iterdir() if p.name != ".gitkeep"} != expected:
        raise GuideError("生成物とマニフェストが一致しません")
    documents = {}
    for filename in expected:
        path = output / filename
        if path.is_symlink() or not path.is_file() or Path(filename).name != filename:
            raise GuideError("生成物のパスが不正です")
        content = path.read_text(encoding="utf-8")
        inspect_text(content)
        if not content.strip():
            raise GuideError("空の生成物があります")
        if filename.endswith(".html"):
            document = Document()
            document.feed(content)
            document.close()
            if (document.errors or document.stack or document.lang != "ja" or not document.charset
                    or not "".join(document.title).strip() or not "".join(document.headings).strip()
                    or not document.metas.get("description") or not document.metas.get("viewport")):
                raise GuideError(f"HTML検証に失敗: {filename}")
            indexable = document.metas.get("robots") == "index,follow"
            canonical = [site_url.rstrip("/") + "/" + filename] if indexable and site_url else []
            if document.canonical != canonical or (indexable and not site_url):
                raise GuideError("canonicalまたはsite_urlが不正です")
            documents[filename] = document
            if filename.startswith("event-"):
                from .core import parse_time
                if not document.provenance:
                    raise GuideError("イベントページの出典がありません")
                for provenance in document.provenance:
                    parse_time(provenance.get("data-verified-at"))
    if "_headers" in expected:
        actual_headers = (output / "_headers").read_text(encoding="utf-8")
        any_indexable = any(doc.metas.get("robots") == "index,follow"
                            for doc in documents.values())
        if actual_headers != cloudflare_headers(not any_indexable):
            raise GuideError("CloudflareのHTTPヘッダーが検索登録条件と一致しません")
    for filename, document in documents.items():
        for link in document.links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                safe_url(link)
            else:
                target = parts.path or filename
                if target not in expected or Path(target).name != target or parts.query:
                    raise GuideError(f"ローカルリンク切れ: {filename}")
                if parts.fragment and (target not in documents or parts.fragment not in documents[target].ids):
                    raise GuideError("ページ内リンク切れです")
    if "sitemap.xml" in expected:
        if not site_url:
            raise GuideError("site_url未確定でsitemapを生成できません")
        xml = ET.fromstring((output / "sitemap.xml").read_text())
        locations = [node.text for node in xml.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        valid = {site_url.rstrip("/") + "/" + name for name, doc in documents.items() if doc.metas["robots"] == "index,follow"}
        if not locations or len(locations) != len(set(locations)) or set(locations) != valid:
            raise GuideError("sitemapに非公開・不正なURLがあります")
    return manifest


@serialized
def build(root, now, output=None):
    output = Path(output) if output else root / "docs"
    if output.is_symlink() or output.parent.resolve() != root.resolve() or output.name != "docs":
        raise GuideError("生成先はリポジトリ直下のdocsのみです")
    files, page_state = create_files(root, now)
    if output.exists():
        previous = read_json(output / ".guide-manifest.json")["files"] if (output / ".guide-manifest.json").exists() else []
        known = set(previous) | {".gitkeep", ".guide-manifest.json"}
        if any(p.name not in known or p.is_symlink() or not p.is_file() for p in output.iterdir()):
            raise GuideError("docsに生成管理外のファイルがあります。上書きせず停止します")
    staging = Path(tempfile.mkdtemp(prefix=".guide-build-", dir=root))
    backup = None
    try:
        for filename, content in files.items():
            (staging / filename).write_text(content, encoding="utf-8")
        if (output / ".gitkeep").exists():
            shutil.copy2(output / ".gitkeep", staging / ".gitkeep")
        rules = read_json(root / "config/page_rules.json")
        result = validate_site(staging, rules["site_url"])
        # Complete persistent-state writes before swapping in verified output.
        atomic_json(root / "cache/page_state.json", page_state)
        if output.exists():
            backup = Path(tempfile.mkdtemp(prefix=".guide-backup-", dir=root))
            backup.rmdir()
            os.replace(output, backup)
        try:
            os.replace(staging, output)
        except OSError:
            if backup:
                os.replace(backup, output)
                backup = None
            raise
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        if backup and backup.exists():
            shutil.rmtree(backup)
