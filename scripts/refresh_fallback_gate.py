"""Fail-closed guard for the second JST daily schedule; never call the CSV here."""
import json
import os
from urllib.request import Request, urlopen

from localguide.core import GuideError, now_jst, parse_time

REPO = "noranamani/noranamani-local-guide"
WORKFLOW = "refresh-approved-places.yml"
API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/runs?per_page=100"


def should_proceed(runs, now, current_run_id):
    """Allow backup only when its own run is visible and there was no earlier
    schedule/manual attempt created on the same JST calendar day.
    This intentionally rejects retries when a failed job may have spent quota.
    """
    ids = {r.get("id") for r in runs}
    if current_run_id not in ids:
        raise GuideError("予備実行の本人確認が未完了です。取得しません")
    for run in runs:
        if run.get("id") == current_run_id:
            continue
        if run.get("event") not in ("schedule", "workflow_dispatch"):
            continue
        created = parse_time(run["created_at"])
        if created.date() == now.date() and created <= now:
            return False
    return True


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise GuideError("許可されていないリポジトリです")
    token = os.environ.get("GITHUB_TOKEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not token or not run_id or not run_id.isdecimal():
        raise GuideError("GitHubの実行認証が不足しています")
    req = Request(API, headers={
        "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "harima-schedule-guard",
    })
    try:
        with urlopen(req, timeout=15) as response:
            document = json.load(response)
        runs = document["workflow_runs"]
        proceed = should_proceed(runs, now_jst(), int(run_id))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # API outages / missing fields fail closed; no API retry and no CSV request.
        print("GitHub実行履歴を検証できないため予備取得を停止しました")
        raise SystemExit(1) from None
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write("proceed=" + ("true" if proceed else "false") + "\n")
    print("予備取得を許可（当日の先行実行なし）" if proceed
          else "当日の先行実行が存在するため予備取得は省略しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
