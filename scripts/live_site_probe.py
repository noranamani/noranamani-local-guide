"""Public Cloudflare Pages verification, covering every current HTML/CSS/image.

Only this site's hostname is contacted. External source and ad links are
checked offline, but never fetched.
"""
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from localguide.core import read_json

BASE = "https://harima-yorimichi.pages.dev"
LIMIT_BYTES = 2 * 1024 * 1024
PAGES = {
    "/": ("はりまよりみち",),
    "/official-events.html": ("地域のイベント情報を探す",
                              "高砂市 イベントカレンダー",
                              "播磨町 イベントカレンダー",
                              "稲美町 イベントカレンダー"),
    "/travel.html": ("家族旅行", "trip-himeji-ako-family-one-night.html"),
    "/trip-himeji-ako-family-one-night.html": ("姫路と赤穂1泊2日",),
    "/places.html": ("明石市立天文科学館",),
}
ROBOTS = re.compile(r'<meta\s+name="robots"\s+content="noindex,follow"', re.I)
MIME = {".html": "text/html", ".css": "text/css",
        ".svg": "image/svg+xml", ".webp": "image/webp"}


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ("a", "link") and values.get("href"):
            self.links.append(values["href"])
        if tag in ("img", "source") and values.get("src"):
            self.links.append(values["src"])


def inventory(root):
    output = Path(root) / "docs"
    files = read_json(output / ".guide-manifest.json").get("files")
    if (not isinstance(files, list) or any(not isinstance(n, str) for n in files)
            or len(set(files)) != len(files)):
        raise ValueError("生成ファイル一覧が不正です")
    if not {"index.html", "nearby.html", "places.html", "official-events.html",
            "travel.html", "styles.css"} <= set(files):
        raise ValueError("主要ページが生成されていません")
    result = []
    for name in sorted(files):
        if name == "_headers":
            continue
        if not name or name.startswith(".") or Path(name).name != name or "\\" in name:
            raise ValueError("生成ファイル名が安全でありません")
        if Path(name).suffix in MIME:
            path = output / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("生成ファイルが存在しません")
            result.append(name)
    return result


def url_path(name):
    return "/" if name == "index.html" else "/" + name


def evaluate(path, body, headers):
    errors = []
    if not ROBOTS.search(body):
        errors.append("noindex指定がありません")
    for value in PAGES.get(path, ()):
        if value not in body:
            errors.append("主要な表示内容が不足: " + value)
    robot_header = headers.get("X-Robots-Tag") or headers.get("x-robots-tag")
    if robot_header and "noindex" not in robot_header.lower():
        errors.append("HTTP robots指定が不正です")
    return errors


def local_reference_errors(route, html, expected):
    parser = References()
    parser.feed(html)
    errors = []
    for link in parser.links:
        url = urlsplit(link)
        if url.scheme in ("http", "https") and url.hostname != urlsplit(BASE).hostname:
            continue
        if url.scheme and url.scheme != "https":
            errors.append("ローカルリンクの形式が不正")
            continue
        if url.netloc and url.hostname != urlsplit(BASE).hostname:
            continue
        if not url.path:
            continue
        path = urlsplit(urljoin(route, url.path)).path.lstrip("/") or "index.html"
        if path not in expected:
            errors.append("配信対象外の内部リンク: " + path)
    return errors


def fetch(path):
    request = Request(BASE + path, headers={
        "User-Agent": "harima-yorimichi-live-smoke/2.0",
        "Accept": "*/*", "Accept-Encoding": "identity"})
    with urlopen(request, timeout=20) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != urlsplit(BASE).hostname:
            raise ValueError("未許可ホストへのリダイレクト")
        if response.status != 200:
            raise ValueError("HTTP 200以外")
        data = response.read(LIMIT_BYTES + 1)
        if not data or len(data) > LIMIT_BYTES:
            raise ValueError("配信ファイルのサイズ異常")
        return data, dict(response.headers)


def check(name, root, expected, loader=fetch):
    route = url_path(name)
    data, headers = loader(route)
    mime = MIME[Path(name).suffix]
    actual = (headers.get("Content-Type") or headers.get("content-type") or "").split(";")[0].strip().lower()
    if actual != mime:
        return ["Content-Type不一致: " + name + " (" + actual + ")"]
    if mime == "text/html":
        html = data.decode("utf-8")
        return evaluate(route, html, headers) + local_reference_errors(route, html, expected)
    if mime == "image/webp" and (data[:4] != b"RIFF" or data[8:12] != b"WEBP"):
        return ["WebPの形式が不正: " + name]
    local = (Path(root) / "docs" / name).read_bytes()
    if hashlib.sha256(local).digest() != hashlib.sha256(data).digest():
        return ["画像・CSSが生成物と一致しません: " + name]
    return []


def main():
    root = Path(__file__).resolve().parents[1]
    names = inventory(root)
    expected = set(names)
    pending = set(names)
    errors = {}
    for attempt in range(4):
        for name in sorted(pending):
            try:
                problems = check(name, root, expected)
            except (HTTPError, URLError, TimeoutError, OSError, UnicodeError,
                    ValueError) as exc:
                problems = ["取得・配信の検証失敗: " + type(exc).__name__]
            if problems:
                errors[name] = problems
                print("未確認:", name, " / ".join(problems), flush=True)
            else:
                pending.discard(name)
                errors.pop(name, None)
                print("OK:", name, flush=True)
        if not pending:
            pages = sum(n.endswith(".html") for n in names)
            print(f"全公開ファイルの検証成功: HTML {pages}件 / CSS・画像 {len(names)-pages}件"
                  f" / 合計 {len(names)}件", flush=True)
            return 0
        if attempt < 3:
            time.sleep(8)
    for name, messages in errors.items():
        print("FAIL:", name, " / ".join(messages), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
