"""Import URLs from saved Google Alerts mail / Atom / RSS, **offline only**.

A locally exported .eml/.xml/.rss under gitignored cache/ may be processed.
Never accesses Gmail, Google, a third-party domain or the network.
Never persists message text, article content, images, or feed metadata.
Outputs only vetted source URLs to cache/event_candidates.json via the
existing review-only queue. This is not an unattended Gmail connector.
"""
import argparse
from email import policy
from email.parser import BytesParser
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree

from localguide.core import GuideError, safe_url
from localguide.official_event_hub import OFFICIAL_HOSTS
from scripts.event_candidates import add_candidates

MAX_INPUT_BYTES = 512 * 1024
MAX_INPUT_FILES = 50
MAX_URLS_PER_RUN = 100
ALLOWED_HOSTS = OFFICIAL_HOSTS | frozenset({
    "kakogawa-note.com",
    "www.kakogawa-note.com",
    "abc-housing.asahi.co.jp",
})
MARKETING_KEYS = frozenset({"fbclid", "gclid", "msclkid", "mc_cid", "mc_eid"})
TRUSTED_REDIRECT_HOSTS = frozenset({"www.google.com", "google.com"})


def normalize_candidate_url(value):
    """Get a safe underlying HTTPS article URL; never make an HTTP request."""
    if not isinstance(value, str) or len(value) > 4096:
        return None
    value = unescape(value.strip())
    try:
        parsed = urlsplit(value)
        if (parsed.hostname in TRUSTED_REDIRECT_HOSTS
                and parsed.scheme == "https" and parsed.path == "/url"):
            redirect = parse_qs(parsed.query, keep_blank_values=False)
            value = (redirect.get("url") or redirect.get("q") or [""])[0]
            parsed = urlsplit(value)
        if parsed.hostname not in ALLOWED_HOSTS or parsed.scheme != "https":
            return None
        if parsed.username or parsed.password or parsed.port not in (None, 443):
            return None
        query_items = [
            (key, content) for key, content in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in MARKETING_KEYS
        ]
        candidate = urlunsplit((
            "https", parsed.netloc.lower(), parsed.path or "/",
            urlencode(query_items), "",
        ))
        return safe_url(candidate)
    except (ValueError, GuideError):
        return None


class _HrefCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.urls.append(href)


def _links_from_eml(raw):
    """Read only eligible anchor URLs; ignore metadata, attachments and text."""
    try:
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except (ValueError, TypeError) as exc:
        raise GuideError("メール書式を解析できません") from exc
    hrefs = []
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue
        if part.get_content_type() != "text/html":
            continue
        try:
            html = part.get_content()
        except (UnicodeError, LookupError, ValueError):
            continue
        if not isinstance(html, str) or len(html) > MAX_INPUT_BYTES:
            continue
        parser = _HrefCollector()
        parser.feed(html)
        hrefs.extend(parser.urls)
    return hrefs


def _local_tag(name):
    return name.rsplit("}", 1)[-1]


def _links_from_feed(raw):
    """Atom/RSS links only; ElementTree never downloads external documents."""
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise GuideError("DOCTYPE/ENTITYを含むXMLは読み込めません")
    try:
        feed = ElementTree.fromstring(raw)
    except ElementTree.ParseError as exc:
        raise GuideError("RSS/Atomの書式が不正です") from exc
    if _local_tag(feed.tag) not in {"feed", "rss", "RDF"}:
        raise GuideError("RSS/Atomのルート要素ではありません")
    hrefs = []
    for entry in feed.iter():
        if _local_tag(entry.tag) not in {"entry", "item"}:
            continue
        for child in entry:
            if _local_tag(child.tag) != "link":
                continue
            if child.attrib.get("rel") not in (None, "", "alternate"):
                continue
            href = child.attrib.get("href") or child.text
            if href:
                hrefs.append(href.strip())
    return hrefs


def extract_candidate_urls(source_path, root):
    """Only read local, gitignored input; return deduped safe candidate URLs."""
    source = Path(source_path)
    cache = (Path(root) / "cache").resolve()
    if (source.is_symlink() or not source.is_file()
            or not source.resolve().is_relative_to(cache)):
        raise GuideError("通知ファイルはgit管理外のcache/内に保存してください")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise GuideError("通知ファイルが大きすぎます（上限512KiB）")
    raw = source.read_bytes()
    suffix = source.suffix.lower()
    if suffix == ".eml":
        hrefs = _links_from_eml(raw)
    elif suffix in {".xml", ".rss", ".atom"}:
        hrefs = _links_from_feed(raw)
    else:
        raise GuideError("EML / RSS / Atomのエクスポートだけを受け付けます")
    urls = []
    seen = set()
    for href in hrefs:
        url = normalize_candidate_url(href)
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls


def import_alert_urls(root, paths, dry_run=False):
    """One bounded batch. Invalid input prevents any queue change."""
    root = Path(root)
    if len(paths) > MAX_INPUT_FILES:
        raise GuideError("通知ファイルの数が多すぎます")
    urls = []
    seen = set()
    for path in paths:
        for url in extract_candidate_urls(path, root):
            if url not in seen:
                seen.add(url)
                urls.append(url)
    if len(urls) > MAX_URLS_PER_RUN:
        raise GuideError("候補URLが多すぎます（1回上限100件）")
    if dry_run or not urls:
        return len(urls), 0
    return len(urls), add_candidates(root, urls)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="保存済みGoogle Alertsメール/Atom/RSSからURLのみ非公開キューへ取り込む"
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path, help="cache/配下の.eml/.rss/.xml")
    source.add_argument("--inbox", type=Path, help="cache/配下の保存済み通知ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="件数だけ確認（キューを変更しない）")
    args = parser.parse_args(argv)
    try:
        root = args.root
        if args.file:
            paths = [args.file]
        else:
            inbox = args.inbox
            cache = (root / "cache").resolve()
            if (inbox.is_symlink() or not inbox.is_dir()
                    or not inbox.resolve().is_relative_to(cache)):
                raise GuideError("通知ディレクトリはcache/内に置いてください")
            paths = sorted(p for p in inbox.iterdir()
                           if p.is_file() and p.suffix.lower() in
                           {".eml", ".xml", ".rss", ".atom"})
        unique, newly_added = import_alert_urls(root, paths, args.dry_run)
        print(f"通知ファイル: {len(paths)}件 / 対象URL: {unique}件 / "
              f"非公開候補の新規追加: {newly_added}件"
              + ("（dry-run）" if args.dry_run else ""))
        return 0
    except (GuideError, OSError, UnicodeError) as exc:
        # Never echo message contents or untrusted URL strings.
        print(f"候補URL取り込みを中止しました: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
