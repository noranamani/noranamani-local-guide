"""Read-only human renewal notices for approved local-guide CSV sources."""
import os
from datetime import timedelta
from pathlib import Path

from localguide.core import now_jst, parse_time, read_json

REVIEW_AGE = timedelta(days=30)
REMIND_BEFORE = timedelta(days=7)


def inspect_sources(config, now):
    notices = []
    expired = False
    for source in config["sources"]:
        if source.get("enabled") is not True:
            continue
        remaining = REVIEW_AGE - (now - parse_time(source["checked_at"]))
        if remaining < timedelta(0):
            status = "expired"
            expired = True
        elif remaining <= REMIND_BEFORE:
            status = "due_soon"
        else:
            status = "valid"
        notices.append((source["id"], status, source["checked_at"]))
    return notices, expired


def main():
    config = read_json(Path(__file__).resolve().parents[1] / "config/sources.json")
    notices, expired = inspect_sources(config, now_jst())
    lines = [
        "## はりまよりみち・情報源審査期限",
        "",
        "審査日の自動延長や情報源の自動有効化は行いません。",
        "",
        "| 情報源 | 審査状態 | 前回の人手確認 |",
        "|---|---|---|",
    ]
    for source_id, status, checked_at in notices:
        label = {"valid": "有効", "due_soon": "7日以内に再審査", "expired": "期限切れ"}[status]
        lines.append(f"| {source_id} | {label} | {checked_at} |")
        if status != "valid":
            level = "error" if status == "expired" else "warning"
            print(f"::{level} title=情報源審査期限::{source_id} {label}。"
                  "公式規約・robots・CSVを人手で再確認してください。")
    if not notices:
        lines.append("| 有効化済み情報源なし | - | - |")
    report = "\n".join(lines) + "\n"
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(report)
    else:
        print(report)
    return 1 if expired else 0


if __name__ == "__main__":
    raise SystemExit(main())
