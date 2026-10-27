"""Offline discovery queue: stage links, then manually approve an official event.

Examples:
  python -m scripts.event_candidates add --url https://example.org/a
  python -m scripts.event_candidates add --file candidate_urls.txt
  python -m scripts.event_candidates list
  python -m scripts.event_candidates approve --candidate-id abc... --id event-slug \
      --title "..." --municipality "加古川市" --venue "..." \
      --start-on 2026-11-03 --end-on 2026-11-03 \
      --official-url https://www.city.kakogawa.lg.jp/... \
      --checked-at 2026-10-27T09:00:00+09:00 \
      --review-note "主催者公式ページを人が確認" --owner-reviewed

Never reads any external site or email. The queue stays under gitignored cache/.
Approval edits data/curated_events.json in the working tree, never commits
or publishes it. PR review and owner authorization are still required.
"""
import argparse
import hashlib
from pathlib import Path
import sys

from localguide.core import GuideError, atomic_json, now_jst, read_json, safe_url
from localguide.curated_events import read_curated_events

MAX_CANDIDATES = 500


def queue_path(root):
    return Path(root) / "cache/event_candidates.json"


def read_queue(root):
    path = queue_path(root)
    if not path.exists():
        return {"schema_version": 1, "items": []}
    doc = read_json(path)
    if (not isinstance(doc, dict) or set(doc) != {"schema_version", "items"}
            or doc["schema_version"] != 1 or not isinstance(doc["items"], list)
            or len(doc["items"]) > MAX_CANDIDATES):
        raise GuideError("候補キューの形式が不正です")
    ids = set()
    for item in doc["items"]:
        if not isinstance(item, dict) or set(item) != {"id", "url", "state", "added_at"}:
            raise GuideError("候補レコードの形式が不正です")
        url = safe_url(item["url"])
        expect_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        if item["id"] != expect_id or item["id"] in ids:
            raise GuideError("候補IDが不正または重複しています")
        if item["state"] not in {"needs_primary_confirmation", "approved"}:
            raise GuideError("候補の状態が不正です")
        ids.add(item["id"])
    return doc


def add_candidates(root, urls):
    """Save only pasted URL strings; never fetch any URL or copy article text."""
    doc = read_queue(root)
    ids = {item["id"] for item in doc["items"]}
    new = 0
    for raw in urls:
        url = safe_url(raw.strip())
        candidate_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        if candidate_id in ids:
            continue
        if len(doc["items"]) >= MAX_CANDIDATES:
            raise GuideError("候補キューの上限に達しました")
        doc["items"].append({"id": candidate_id, "url": url,
                             "state": "needs_primary_confirmation",
                             "added_at": now_jst().isoformat()})
        ids.add(candidate_id)
        new += 1
    if new:
        atomic_json(queue_path(root), doc)
    return new


def approve_candidate(root, fields, owner_reviewed=False):
    """Explicit human authorization; cannot be triggered by an untrusted feed."""
    if not owner_reviewed:
        raise GuideError("主催者の公式情報の人手確認と所有者承認が必要です")
    queue = read_queue(root)
    candidate = next((x for x in queue["items"]
                      if x["id"] == fields["candidate_id"]), None)
    if not candidate or candidate["state"] != "needs_primary_confirmation":
        raise GuideError("承認待ちの候補IDが見つかりません")
    path = Path(root) / "data/curated_events.json"
    if not path.is_file():
        raise GuideError("手動イベントの初期データがありません")
    doc = read_json(path)
    event = {
        "id": fields["id"],
        "title": fields["title"],
        "municipality": fields["municipality"],
        "venue": fields["venue"],
        "official_url": fields["official_url"],
        "start_on": fields["start_on"],
        "end_on": fields["end_on"],
        "checked_at": fields["checked_at"],
        "review_state": "approved",
        "review_note": fields["review_note"],
        "information_scope": "facts_only_owner_reviewed",
    }
    # Validation happens before either file is saved. Queued media URLs are not
    # published; only a separately verified organizer's official link is used.
    existing = read_curated_events(root)
    doc["items"] = existing + [event]
    from localguide.curated_events import _validate_events
    _validate_events(doc, now_jst())
    atomic_json(path, doc)
    candidate["state"] = "approved"
    atomic_json(queue_path(root), queue)
    return event["id"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="オフライン候補URL受付・主催者公式確認後の承認")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="action", required=True)
    add = commands.add_parser("add", help="1件または改行区切りURLをローカルキューへ保存")
    add.add_argument("--url", action="append", default=[])
    add.add_argument("--file", type=Path, help="テキストファイル（URLのみ、1行1件）")
    commands.add_parser("list", help="非公開キューの状態を表示")
    approve = commands.add_parser("approve", help="人手確認済み候補をPR審査対象のJSONへ追加")
    for key in ("candidate_id", "id", "title", "municipality", "venue", "start_on",
                "end_on", "official_url", "checked_at", "review_note"):
        approve.add_argument("--" + key.replace("_", "-"), required=True)
    approve.add_argument("--owner-reviewed", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "add":
            urls = list(args.url)
            if args.file:
                if not args.file.is_file() or args.file.stat().st_size > 100_000:
                    raise GuideError("候補URLファイルが不正か大きすぎます")
                urls.extend(x.strip() for x in args.file.read_text(encoding="utf-8").splitlines()
                            if x.strip())
            if not urls or len(urls) > 100:
                raise GuideError("1〜100件のURLを指定してください")
            print(f"追加した未承認候補: {add_candidates(args.root, urls)}件")
        elif args.action == "list":
            doc = read_queue(args.root)
            for item in doc["items"]:
                print(f'{item["id"]}  {item["state"]}  {item["url"]}')
            print(f'候補合計: {len(doc["items"])}件（掲載はしません）')
        else:
            fields = {key: getattr(args, key) for key in (
                "candidate_id", "id", "title", "municipality", "venue",
                "start_on", "end_on", "official_url", "checked_at", "review_note")}
            print(f'承認済みデータへ追加: {approve_candidate(args.root, fields, args.owner_reviewed)}')
        return 0
    except (GuideError, OSError, UnicodeError) as exc:
        print(f"候補確認を中止しました: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
