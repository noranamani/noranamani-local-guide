"""Read-only, reproducible operations health evaluation; issue creation is CI-only."""
import os
from datetime import timedelta
from pathlib import Path

from localguide.core import GuideError, now_jst, parse_time, read_json
from scripts.source_review_health import inspect_sources

MAX_SUCCESS_AGE = timedelta(hours=40)
SOURCE_ID = "akashi_open_data"


def assess(now, config, state, related_conclusion=None):
    """Return stable issue codes (no secret/data payloads) for automatic alerts."""
    notices = []
    enabled = [s for s in config.get("sources", []) if s.get("enabled")]
    if len(enabled) != 1 or enabled[0].get("id") != SOURCE_ID:
        notices.append("source_configuration")
    try:
        for _, status, checked_at in inspect_sources(config, now)[0]:
            if parse_time(checked_at) > now:
                notices.append("source_review_invalid")
            elif status == "expired":
                notices.append("source_review_expired")
            elif status == "due_soon":
                notices.append("source_review_due_soon")
    except (ValueError, TypeError, KeyError):
        notices.append("source_review_invalid")
    records = state.get("sources", {})
    if not isinstance(records, dict):
        records = {}
        notices.append("state_invalid")
    record = records.get(SOURCE_ID, {})
    if not isinstance(record, dict):
        record = {}
        notices.append("state_invalid")
    if record.get("halted"):
        notices.append("access_halted")
    checked = record.get("last_success_at")
    success_today = False
    if not checked:
        notices.append("never_succeeded")
    else:
        try:
            verified = parse_time(checked)
            success_today = verified.date() == now.date()
            age = now - verified
            if age < timedelta(0):
                notices.append("future_success_timestamp")
            elif age > MAX_SUCCESS_AGE:
                notices.append("daily_success_stale")
        except (ValueError, TypeError):
            notices.append("invalid_success_timestamp")
    if (record.get("attempt_day") == now.date().isoformat()
            and record.get("last_error") and not success_today):
        notices.append("daily_attempt_failed")
    if related_conclusion and related_conclusion not in ("success", "skipped"):
        notices.append("workflow_failure")
    return sorted(set(notices))


def main():
    root = Path(__file__).resolve().parents[1]
    now = now_jst()
    preliminary = []
    try:
        config = read_json(root / "config/sources.json")
    except GuideError:
        config = {"sources": []}
        preliminary.append("config_read_error")
    try:
        state = read_json(root / "data/source_state.json")
    except GuideError:
        state = {"sources": {}}
        preliminary.append("state_read_error")
    reasons = sorted(set(
        assess(now, config, state, os.getenv("RELATED_CONCLUSION")) + preliminary
    ))
    print("運用診断: " + (", ".join(reasons) if reasons else "正常"))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("## はりまよりみち 自動更新の稼働確認\n\n")
            stream.write(f"- 確認日時（JST）: {now.isoformat()}\n")
            stream.write(f"- 状態: {', '.join(reasons) if reasons else '問題未検出'}\n")
            stream.write("- 取得失敗時は日次上限を守り、自動的に2回目の外部取得をしません。\n")
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"alert={'true' if reasons else 'false'}\n")
            stream.write(f"codes={','.join(reasons)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
