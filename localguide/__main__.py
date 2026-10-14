"""Noninteractive local CLI. It never publishes, pushes, or registers schedules."""
import argparse
import sys
from pathlib import Path

from .core import GuideError, now_jst, parse_time, read_json
from .site import build, validate_site
from .sources import collect
from .validation import validate_data


def main(argv=None):
    parser = argparse.ArgumentParser(description="noranamani LOCAL GUIDE の取得・検証・静的サイト生成")
    parser.add_argument("command", choices=("collect", "validate", "build", "run"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--now", help="オフライン検証用のタイムゾーン付きISO8601日時")
    parser.add_argument("--site", action="store_true", help="validate時に既存docsも検証")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        now = parse_time(args.now) if args.now else now_jst()
        if args.command in ("collect", "run"):
            summaries, failures = collect(root, now)
            for line in summaries:
                print(line)
            if failures:
                for line in failures:
                    print(line, file=sys.stderr)
                return 1
        if args.command == "validate":
            data = validate_data(root, now)
            print(f"JSONスキーマ・参照・日時・秘密値検証: 成功 ({len(data)}データセット)")
            if args.site:
                result = validate_site(root / "docs", read_json(root / "config/page_rules.json")["site_url"])
                print(f"HTML・ローカルリンク・SEO検証: 成功 ({len(result['files'])}ファイル)")
        if args.command in ("build", "run"):
            result = build(root, now)
            print(f"サイト生成・検証: 成功 (イベント{result['events']}件・施設{result['places']}件)")
        return 0
    except (GuideError, KeyError, TypeError, OSError, ValueError):
        # Detailed GuideError messages are safe; unexpected exceptions must not leak raw source data.
        exc = sys.exc_info()[1]
        print(f"停止: {exc}" if isinstance(exc, GuideError) else "停止: ファイル・設定の形式またはI/Oが不正です", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
