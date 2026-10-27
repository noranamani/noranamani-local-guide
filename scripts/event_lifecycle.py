"""Review expiry, stale confirmations and duplicates without accessing event sources."""
import argparse
import sys
from pathlib import Path

from localguide.core import GuideError, atomic_json, now_jst, parse_time, read_json
from localguide.curated_events import event_state, read_curated_events


def lifecycle(root, now=None, apply=False):
    now = now or now_jst()
    path = Path(root) / "data/curated_events.json"
    if not path.is_file():
        return {"total": 0, "approved": 0, "needs_recheck": 0, "expired": 0, "changed": 0}
    # Strict validation catches duplicate IDs, URLs and occurrence details
    # before any mutation. Never refresh verified timestamps automatically.
    events = read_curated_events(root, now)
    doc = read_json(path)
    counts = {"total": len(events), "approved": 0, "needs_recheck": 0,
              "expired": 0, "changed": 0}
    for event in events:
        state = event_state(event, now)
        counts[state] += 1
        if apply and event["review_state"] != state:
            event["review_state"] = state
            counts["changed"] += 1
    if counts["changed"]:
        doc["items"] = events
        atomic_json(path, doc)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="公式イベントの終了・鮮度・重複をオフライン検証")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true",
                        help="承認期限切れだけを公開用JSON内の非公開状態に変更する")
    parser.add_argument("--now", help="テスト用のISO8601日時。通常運用では指定しない")
    args = parser.parse_args(argv)
    try:
        now = parse_time(args.now) if args.now else now_jst()
        counts = lifecycle(args.root, now, args.apply)
        print("手動イベントの検証結果: "
              + " / ".join(f"{key}={value}" for key, value in counts.items()))
        return 0
    except (GuideError, OSError) as exc:
        print(f"安全検証失敗（更新しません）: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
