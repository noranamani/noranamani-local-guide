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

STYLE = """*{box-sizing:border-box}body{margin:0;background:#faf8f3;color:#233d38;font:16px/1.8 system-ui,sans-serif}header,main,footer{max-width:960px;margin:auto;padding:24px}header{border-bottom:3px solid #ddaf54}a{color:#00695c;text-underline-offset:3px}nav{display:flex;gap:20px;flex-wrap:wrap}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:20px}.card,.notice{background:white;border:1px solid #d9e0d7;border-radius:12px;padding:20px;margin:16px 0}h1{font-size:clamp(1.6rem,5vw,2.4rem);line-height:1.4}h2{font-size:1.25rem}dt{font-weight:bold}dd{margin:0 0 8px}.muted,footer{font-size:.9rem;color:#53655e}.tag{display:inline-block;background:#eef2df;padding:2px 10px;border-radius:20px}ul{padding-left:1.3em}a:focus-visible{outline:3px solid #c36f16;outline-offset:3px}"""


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
<title>{escaped(title)} | noranamani LOCAL GUIDE</title><meta name="description" content="{escaped(description)}">
<meta name="robots" content="{robots}">{canonical}<link rel="stylesheet" href="styles.css"></head>
<body><header><a href="index.html">noranamani LOCAL GUIDE</a><p>加古川・明石・姫路と周辺の家族向け地域情報</p>
<nav aria-label="主なページ">{nav}</nav></header><main><h1>{escaped(title)}</h1>{body}</main>
<footer>料金・日程の変更や中止は公式情報をご確認ください。確認できない情報は「不明」と表示します。</footer></body></html>'''


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
    return '<ul class="muted">' + "".join(entries) + "</ul>"


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
    nav = '<a href="index.html">ホーム</a>' + ('<a href="events.html">開催情報一覧</a>' if events else '') + ('<a href="places.html">施設一覧</a>' if places else '')
    files, indexable_files = {"styles.css": STYLE}, []
    url = rules["site_url"]

    def add(filename, title, description, body, indexable):
        files[filename] = page(title, description, body, filename, url, indexable, nav)
        if indexable and url:
            indexable_files.append(filename)

    cards = "".join(event_content(e, sources, now) for e in events)
    place_cards = "".join(place_content(p, sources) for p in places)
    if not events and not places:
        content = '<section class="notice"><h2>掲載準備中です</h2><p>現在、公開できる確認済みの情報はありません。情報源の利用条件と掲載内容を確認してから掲載します。</p></section>'
    else:
        content = ('<h2>開催情報</h2><div class="cards">' + cards + '</div>') if events else ''
        if places:
            content += '<h2>確認済みの施設</h2><div class="cards">' + place_cards + '</div>'
    add("index.html", "家族で出かける地域ガイド", "加古川・明石・姫路周辺の確認済み開催情報と施設案内。公式情報と確認日時を表示します。", content, qualified(events, rules) or places_ready)
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
                                               "files": sorted(files), "events": len(events), "places": len(places)}, ensure_ascii=False, indent=2) + "\n"
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
