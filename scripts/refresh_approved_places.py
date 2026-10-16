"""Daily safety-gated refresh of the *one* reviewed municipal facility CSV.

No source discovery, RSS, third-party text, image download, or ad modification.
Collect in an isolated filesystem; only vetted places and request-state are
copied back to the checkout. GitHub Actions controls committing to main.
"""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import argparse
import os
import shutil
import sys
import tempfile

from localguide.core import GuideError, atomic_json, now_jst, parse_time, read_json
from localguide.sources import approved, collect
from localguide.validation import validate_data
from scripts.cloudflare_build import build_for_cloudflare

SOURCE_ID = "akashi_open_data"
SOURCE_URL = "https://www.city.akashi.lg.jp/documents/29427/282031_tourism.csv"
FAILURE_MESSAGE = "施設CSVの取得または掲載検証に失敗しました。GitHub Actionsを確認してください。"


def _record_attempt_only(root, before, staging_state, message=FAILURE_MESSAGE):
    """Keep a failed request's daily quota and halt flag, never its success stamp."""
    current = deepcopy(before)
    prior = current["sources"].get(SOURCE_ID, {}).copy()
    attempted = staging_state.get("sources", {}).get(SOURCE_ID, {})
    if attempted.get("last_attempt_at") == prior.get("last_attempt_at"):
        return False
    for field in ("attempt_day", "attempts", "last_attempt_at", "halted"):
        if field in attempted:
            prior[field] = attempted[field]
    prior["last_error"] = message
    current["sources"][SOURCE_ID] = prior
    atomic_json(root / "data/source_state.json", current)
    return True


def refresh_once(root, now, fetcher=None, builder=build_for_cloudflare):
    """Return 'updated' or 'skipped', raise GuideError for a failed refresh.

    Only the official Akashi CSV may be called, and only once per JST date.
    On failure, persist only request accounting (and 401/403/429 halt flag),
    so another dispatch cannot silently exceed the reviewed daily limit.
    """
    root = Path(root).resolve()
    registry = read_json(root / "config/sources.json")
    enabled = [source for source in registry["sources"] if source["enabled"]]
    if (len(enabled) != 1 or enabled[0].get("id") != SOURCE_ID
            or enabled[0].get("url") != SOURCE_URL
            or enabled[0].get("adapter") != "places_csv"
            or enabled[0].get("maximum_requests_per_day") != 1):
        raise GuideError("自動更新は明石市の審査済み観光施設CSV1件だけに限定しています")

    source = enabled[0]
    # An expired policy review or an access-denial halt must not be auto-renewed.
    approved(source, now)
    previous_state = read_json(root / "data/source_state.json")
    previous = previous_state["sources"].get(SOURCE_ID, {})
    if previous.get("halted"):
        raise GuideError("アクセス停止中です。取得再開には情報源の手動再審査が必要です")
    if (previous.get("attempt_day") == now.date().isoformat()
            and previous.get("attempts", 0) >= 1):
        return "skipped"

    with tempfile.TemporaryDirectory(prefix="harima-verified-places-") as directory:
        staged = Path(directory)
        for folder in ("config", "data", "schemas"):
            shutil.copytree(root / folder, staged / folder)
        # Validate the checked-in sources/data before any network request.
        validate_data(staged, now)

        before_places = read_json(root / "data/places.json")
        previous_count = sum(
            any(p["source_id"] == SOURCE_ID for p in place["sources"])
            for place in before_places["items"]
        )
        attempted_state = previous_state
        try:
            args = {} if fetcher is None else {"fetcher": fetcher}
            summaries, failures = collect(staged, now, **args)
            attempted_state = read_json(staged / "data/source_state.json")
            if failures:
                raise GuideError("許可済みCSVの取得に失敗しました")
            after_attempt = attempted_state["sources"].get(SOURCE_ID, {})
            if (after_attempt.get("attempt_day") != now.date().isoformat()
                    or after_attempt.get("last_success_at") != now.isoformat()):
                raise GuideError("今回の取得が完了していないため公開データを変更しません")

            new_places = read_json(staged / "data/places.json")
            current_count = sum(
                any(p["source_id"] == SOURCE_ID for p in place["sources"])
                for place in new_places["items"]
            )
            if current_count == 0 or (previous_count and current_count * 4 < previous_count * 3):
                raise GuideError("施設CSVの件数が急減しました。手動審査まで更新しません")

            # Includes static output, HTML/local links, site policies and noindex.
            validate_data(staged, now)
            builder(staged, now)
            # Only after ALL checks succeed may the public source snapshot change.
            atomic_json(root / "data/places.json", new_places)
            atomic_json(root / "data/source_state.json", attempted_state)
            print(f"公式施設CSVの検証成功: {previous_count}件 → {current_count}件（出典 {SOURCE_ID}）")
            for summary in summaries:
                print(summary)
            return "updated"
        except (GuideError, OSError, ValueError, TypeError, KeyError) as error:
            # collect() writes its attempt reservation before touching the wire.
            # Even if the site build rejects a downloaded CSV, do not record
            # the unvalidated success stamp or replace the last good data.
            if not isinstance(error, GuideError):
                message = FAILURE_MESSAGE
            elif attempted_state.get("sources", {}).get(SOURCE_ID, {}).get("halted"):
                message = "公式CSVがアクセス拒否されました。手動再審査まで取得を停止します。"
            else:
                message = FAILURE_MESSAGE
            _record_attempt_only(root, previous_state, attempted_state, message)
            raise GuideError(message) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description="明石市の許可済み施設CSVだけを安全に更新")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        now = now_jst()
        result = refresh_once(args.root, now)
        if result == "skipped":
            print("本日は既に取得済みです。日次上限を守るため再取得しません")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write(
                    "### はりまよりみち・公式施設データ確認\n\n"
                    f"- 日時（日本時間）: {now.isoformat()}\n"
                    f"- 情報源: {SOURCE_ID}（審査済みの明石市CSVのみ）\n"
                    f"- 処理: {result}\n"
                    "- 情報源の再利用許諾は自動更新せず、30日以内に人手で再審査\n"
                )
        return 0
    except GuideError as error:
        # All failures are pre-reviewed human-readable messages; never log
        # remote CSV bodies, network headers or private environment values.
        print(f"施設データ更新停止: {error}", file=sys.stderr)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write(
                    "### はりまよりみち・公式施設データ更新停止\n\n"
                    "- 既存の掲載データは更新していません。\n"
                    "- 取得に失敗した場合、次回の通常ビルドでは古い施設を非表示にします。\n"
                    "- GitHub Actionsログとdata/source_state.jsonの停止状態を確認してください。\n"
                )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
