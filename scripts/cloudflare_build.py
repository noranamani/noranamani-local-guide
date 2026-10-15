"""Build the static output for a future Cloudflare Pages deployment.

This only uses committed JSON records. No external collection, credential
usage, network calls, repository writes or live deployment is performed.
Cloudflare Git integration, if configured, deploys the resulting docs/ itself.
"""
import argparse
import sys
from pathlib import Path

from localguide.core import GuideError, now_jst, parse_time, read_json
from localguide.site import build, validate_site


def build_for_cloudflare(root, now=None):
    root = Path(root).resolve()
    now = now or now_jst()
    info = build(root, now)
    rules = read_json(root / "config/page_rules.json")
    check = validate_site(root / "docs", rules["site_url"])
    if info != check or "_headers" not in check["files"]:
        raise GuideError("Cloudflare Pages出力の検証に失敗しました")
    print("Cloudflare Pages向け静的ビルド・検証成功"
          f" (イベント{check['events']}件・施設{check['places']}件)")
    return check


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cloudflare Pages用オフラインビルド（デプロイ不可）")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--now", help="テスト専用のタイムゾーン付きISO8601日時")
    args = parser.parse_args(argv)
    try:
        now = parse_time(args.now) if args.now else now_jst()
        build_for_cloudflare(args.root, now)
    except (GuideError, OSError, ValueError, TypeError, KeyError):
        print("Cloudflare Pagesビルドを停止しました。元のJSONデータ・公開条件を確認してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
