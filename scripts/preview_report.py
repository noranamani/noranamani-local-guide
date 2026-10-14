"""Describe generated, *unpublished* static site safely; never fetch data."""
import argparse
import json
import os
from pathlib import Path

from localguide.core import read_json

def preview_status(root):
    root = Path(root)
    manifest = read_json(root / "docs/.guide-manifest.json")
    sources = read_json(root / "config/sources.json")["sources"]
    html_files = sorted(x for x in manifest["files"] if x.endswith(".html"))
    searchable, private = [], []
    for name in html_files:
        content = (root / "docs" / name).read_text(encoding="utf-8")
        if '<meta name="robots" content="index,follow">' in content:
            searchable.append(name)
        elif '<meta name="robots" content="noindex,follow">' in content:
            private.append(name)
        else:
            raise ValueError("想定外の検索エンジン設定が見つかりました")
    site_url = read_json(root / "config/page_rules.json")["site_url"]
    if not site_url and searchable:
        raise ValueError("site_urlが未設定なのに検索対象となるページがあります")
    return {
        "generated_at": manifest["generated_at"],
        "events": manifest["events"], "places": manifest["places"],
        "sources_total": len(sources),
        "sources_enabled": sum(s["enabled"] for s in sources),
        "html_total": len(html_files),
        "html_indexable": len(searchable),
        "html_noindex": len(private),
        "sitemap": "sitemap.xml" in manifest["files"],
        "site_url_configured": bool(site_url),
    }

def markdown_report(result):
    sections = [
        "## noranamani LOCAL GUIDE — 未公開プレビュー",
        "",
        "この結果はGitHub Actions内で生成したものです。**GitHub Pagesへの公開や外部情報取得は行っていません。**",
        "",
        "| 確認項目 | 結果 |",
        "|---|---:|",
        f"| 生成日時 | {result['generated_at']} |",
        f"| 掲載対象のイベント | {result['events']}件 |",
        f"| 掲載対象の施設 | {result['places']}件 |",
        f"| 情報源（有効 / 候補含む全数） | {result['sources_enabled']} / {result['sources_total']} |",
        f"| HTMLファイル数 | {result['html_total']} |",
        f"| 検索対象 / noindex | {result['html_indexable']} / {result['html_noindex']} |",
        f"| sitemap生成 | {'あり' if result['sitemap'] else 'なし'} |",
        f"| site_url設定済み | {'はい' if result['site_url_configured'] else 'いいえ'} |",
    ]
    if not result["events"]:
        sections.extend(["", "**注意:** 掲載できるイベントはまだ0件。開催予定を推測して補いません。"])
    if not result["site_url_configured"]:
        sections.extend(["", "**注意:** 正式な公開URLが未設定なので、検索登録しません。"])
    return "\n".join(sections) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path, default=Path("preview-report.md"))
    args = parser.parse_args()
    report = markdown_report(preview_status(args.root.resolve()))
    args.output.write_text(report, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(report)
    print(report)

if __name__ == "__main__":
    main()
