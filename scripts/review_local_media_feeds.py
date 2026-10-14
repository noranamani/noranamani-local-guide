"""One-off feed format and freshness survey; no article content is persisted.

Discovery does NOT grant permission to republish. Follow robots and never try
authentication, redirects or access-control workarounds.
"""
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

SITES = {
    "kakogawa_note": "https://kakogawa-note.com/feed/",
    "akashi_journal": "https://akashi-journal.com/feed/",
    "himeji_no_tane": "https://budou-chan.jp/feed/",
    "kakogawa_no_koto": "https://harimania.com/feed/",
}
USER_AGENT = "noranamani-local-guide/0.1 (+https://github.com/noranamani/noranamani-local-guide; one-time feed-policy survey)"
MAX_ROBOTS = 100 * 1024
MAX_FEED = 2 * 1024 * 1024
KEYWORDS = ("イベント", "週末", "マルシェ", "開店", "閉店", "オープン",
            "フェス", "ワークショップ", "子ども", "こども", "ハロウィン")

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unreviewed redirect")

def fetch(url, limit):
    opener = build_opener(NoRedirect())
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/plain, */*;q=0.1",
                                "Accept-Encoding": "identity"})
    with opener.open(req, timeout=12) as response:
        if response.geturl() != url:
            raise ValueError("unreviewed redirect")
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("response too large")
        return body, response.headers.get_content_type()

def robots_decision(url):
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        body, _ = fetch(robots_url, MAX_ROBOTS)
        content = body.decode("utf-8-sig", errors="replace")
        parser = RobotFileParser()
        parser.parse(content.splitlines())
        return (parser.can_fetch(USER_AGENT, url), "robots present")
    except HTTPError as e:
        if e.code in (404, 410):
            return True, f"robots HTTP {e.code}"
        return False, f"robots HTTP {e.code} (not authorized to probe feed)"
    except (ValueError, URLError, TimeoutError, OSError, UnicodeError):
        return False, "robots inaccessible, feed not probed"

def name_without_ns(tag):
    return tag.rsplit("}", 1)[-1]

def text_of(item, names):
    for element in item:
        if name_without_ns(element.tag) in names and element.text:
            return element.text.strip()
    return ""

def parse_date(value):
    if not value:
        return None
    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc).date().isoformat()

def inspect_xml(body):
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise ValueError("not parseable XML")
    kind = name_without_ns(root.tag).lower()
    if kind in ("rss", "rdf"):
        items = [x for x in root.iter() if name_without_ns(x.tag) == "item"]
    elif kind == "feed":
        items = [x for x in root.iter() if name_without_ns(x.tag) == "entry"]
    else:
        raise ValueError("XML is not RSS or Atom")
    if not items:
        return {"format": kind, "entries": 0, "latest_published": None,
                "earliest_published": None, "relevant_title_keywords": 0}
    observed, keyword_count = [], 0
    for item in items[:100]:
        title = text_of(item, {"title"})
        keyword_count += any(word in title for word in KEYWORDS)
        date_value = text_of(item, {"pubDate", "published", "updated", "date"})
        day = parse_date(date_value)
        if day:
            observed.append(day)
    return {"format": kind, "entries": len(items), "latest_published": max(observed) if observed else None,
            "earliest_published": min(observed) if observed else None,
            "relevant_title_keywords": keyword_count,
            "counts_are_discovery_only": True}

def main():
    for name, url in SITES.items():
        result = {"site": name, "candidate": url, "republication_rights": "unverified"}
        try:
            allowed, robots = robots_decision(url)
            result["robots"] = robots
            if not allowed:
                result["feed"] = "not tested due to robots status"
            else:
                body, content_type = fetch(url, MAX_FEED)
                result["content_type"] = content_type
                result.update(inspect_xml(body))
                result["feed"] = "readable for one-time metadata audit"
        except HTTPError as e:
            result["feed"] = f"HTTP {e.code}"
        except (URLError, TimeoutError, ValueError, OSError, UnicodeError) as e:
            result["feed"] = f"unavailable ({type(e).__name__})"
        print(json.dumps(result, ensure_ascii=False))
    print("No feed entries, titles, body text or images saved. No publication authorized.")

if __name__ == "__main__":
    main()
