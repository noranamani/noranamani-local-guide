"""One-shot, privacy-preserving header/category survey of official Akashi open CSV.

No data records are retained or printed. This is an audit utility, NOT an
approved source adapter. It does not modify config, data, or published pages.
"""
import csv
import io
import json
import re
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

URL = "https://www.city.akashi.lg.jp/documents/29427/282031_preschool.csv"
MAX_BYTES = 256 * 1024
USER_AGENT = "noranamani-local-guide/0.1 (one-time official open data metadata audit)"
SELECTORS = ("種類", "分類", "種別", "区分", "施設タイプ", "施設種")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("redirect not approved")


def get_csv():
    opener = build_opener(NoRedirect())
    request = Request(URL, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/csv, application/csv, application/octet-stream",
        "Accept-Encoding": "identity",
    })
    with opener.open(request, timeout=20) as response:
        if response.geturl() != URL:
            raise ValueError("redirect not approved")
        content_type = response.headers.get_content_type()
        if content_type not in {"text/csv", "application/csv", "application/octet-stream", "text/plain"}:
            raise ValueError("unexpected content type")
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("CSV exceeds audit limit")
        return body, content_type


def inspect(body):
    if body.startswith(b"PK") or body.lstrip().startswith(b"<"):
        raise ValueError("expected CSV, not ZIP or HTML")
    for encoding in ("utf-8-sig", "cp932"):
        try:
            content = body.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("unsupported CSV encoding")
    reader = csv.DictReader(io.StringIO(content), strict=True)
    columns = reader.fieldnames
    if not columns or len(columns) > 200 or any(not c or len(c) > 100 for c in columns):
        raise ValueError("invalid CSV header")
    types = {c: Counter() for c in columns if any(sel in c for sel in SELECTORS)}
    url_columns = [c for c in columns if re.search(r"(?i)(URL|ホームページ|ウェブサイト|Webサイト)", c)]
    url_counts = {name: 0 for name in url_columns}
    valid = 0
    for row in reader:
        if valid >= 5000 or None in row or any(v is None for v in row.values()):
            raise ValueError("unexpected rows")
        valid += 1
        for name in types:
            value = row[name].strip()
            if value and len(value) <= 60:
                types[name][value] += 1
        for name in url_columns:
            value = row[name].strip()
            parts = urlsplit(value)
            if parts.scheme == "https" and parts.hostname:
                url_counts[name] += 1
    # Category values can be safely aggregated but not individual facility names
    # or contact details. Limit to a few short labels.
    types = {name: sorted(counter.items(), key=lambda p: (-p[1], p[0]))[:12]
             for name, counter in types.items() if counter}
    return {"csv_rows": valid, "headers": columns,
            "category_value_counts": types, "https_url_counts_by_column": url_counts}


if __name__ == "__main__":
    try:
        body, kind = get_csv()
        report = inspect(body)
        report["source"] = "明石市公式オープンデータ「子育て施設一覧」"
        report["http_content_type"] = kind
        report["record_level_data_retained"] = False
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (HTTPError, URLError, ValueError, csv.Error, OSError) as err:
        # Do not expose response bodies or user-provided data in logs.
        print("公式CSVメタデータ調査は失敗しました。HTTPまたはCSV形式の問題です。")
        raise SystemExit(1)
