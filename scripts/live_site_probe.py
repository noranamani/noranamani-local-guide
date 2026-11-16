"""Read-only HTTPS checks against the public Cloudflare Pages deployment.

No credentials, page modification, scraping of unrelated sites, or downloads.
Run by GitHub Actions because local ChatGPT tooling may not reach pages.dev.
"""
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

BASE = "https://harima-yorimichi.pages.dev"
LIMIT_BYTES = 2 * 1024 * 1024
PAGES = {
    "/": ("はりまよりみち",),
    "/official-events.html": (
        "地域のイベント情報を探す", "高砂市 イベントカレンダー",
        "播磨町 イベントカレンダー", "稲美町 イベントカレンダー",
    ),
    "/travel.html": ("家族旅行", "trip-himeji-ako-family-one-night.html"),
    "/trip-himeji-ako-family-one-night.html": ("姫路と赤穂1泊2日",),
    "/places.html": ("明石市立天文科学館",),
}
ROBOTS = re.compile(r'<meta\s+name="robots"\s+content="noindex,follow"', re.I)


def evaluate(path, body, headers):
    errors = []
    if not ROBOTS.search(body):
        errors.append("HTMLのnoindex指定がありません")
    for value in PAGES[path]:
        if value not in body:
            errors.append("必要なコンテンツが見つかりません: " + value)
    robot_header = headers.get("X-Robots-Tag") or headers.get("x-robots-tag")
    if robot_header and "noindex" not in robot_header.lower():
        errors.append("HTTPのrobots指定が想定と異なります")
    return errors


def fetch(path):
    url = BASE + path
    request = Request(url, headers={
        "User-Agent": "harima-yorimichi-live-smoke/1.0",
        "Accept": "text/html",
    })
    with urlopen(request, timeout=20) as response:
        final = urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname != urlsplit(BASE).hostname:
            raise ValueError("未許可ドメインへのリダイレクトを検出")
        if response.status != 200:
            raise ValueError("HTTP 200以外")
        media_type = response.headers.get_content_type()
        if media_type != "text/html":
            raise ValueError("HTML以外のレスポンス")
        content = response.read(LIMIT_BYTES + 1)
        if len(content) > LIMIT_BYTES:
            raise ValueError("HTMLがサイズ上限を超過")
        return content.decode("utf-8"), dict(response.headers)


def main():
    remaining = set(PAGES)
    last_failures = {}
    # Pages deployment may lag behind the main commit. Retry only our own
    # public pages and never touch the CSV acquisition rate limit.
    for attempt in range(1, 5):
        for path in sorted(remaining):
            try:
                html, headers = fetch(path)
                errors = evaluate(path, html, headers)
            except (HTTPError, URLError, TimeoutError, OSError, UnicodeError,
                    ValueError) as exc:
                errors = ["HTTPS/HTTP取得に失敗: " + type(exc).__name__]
            if errors:
                last_failures[path] = errors
                print("未確認:", path, " / ".join(errors), flush=True)
            else:
                print("OK:", path, "noindex・主要コンテンツ確認", flush=True)
                last_failures.pop(path, None)
                remaining.discard(path)
        if not remaining:
            print("公開ページ5件のHTTP・主要コンテンツ検証が完了しました", flush=True)
            return 0
        if attempt < 4:
            time.sleep(8)
    print("公開ページの検証に失敗しました。Cloudflare Pagesのデプロイ状況を確認してください。",
          file=sys.stderr)
    for path, errors in last_failures.items():
        print(path, ": ", " / ".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
