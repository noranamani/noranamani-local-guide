"""Manual offline entrypoint. This does not fetch RSS or publish pages."""
import argparse
import sys
from pathlib import Path

from localguide.core import GuideError, now_jst
from localguide.rss_discovery import stage_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description="承認済みRSSスナップショットから内部確認キューを作成（通信なし）")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--xml-file", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    try:
        counts = stage_snapshot(args.root.resolve(), args.source_id, args.xml_file, now_jst())
    except (GuideError, OSError, ValueError):
        print("RSS確認キューの作成を停止しました。審査状態・入力XML・保存先を確認してください。", file=sys.stderr)
        return 1
    print(f"確認候補: {counts['discovered']}件 / キュー合計: {counts['queued']}件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
