"""Write a no-network launch-readiness report after static site validation."""
import argparse
import sys
from pathlib import Path

from localguide.core import GuideError, now_jst, parse_time
from localguide.release_readiness import assess, markdown_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="LOCAL GUIDE公開前レポート（非公開）")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("launch-readiness-report.md"))
    parser.add_argument("--now", help="テスト向けのタイムゾーン付き日時")
    args = parser.parse_args(argv)
    try:
        result = assess(args.root, parse_time(args.now) if args.now else now_jst())
        report = markdown_report(result)
        args.output.write_text(report, encoding="utf-8")
        print(report)
    except (GuideError, OSError, ValueError, KeyError, TypeError):
        print("公開前チェックを停止しました。検証済みのdocsと設定を確認してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
