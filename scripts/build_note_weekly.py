#!/usr/bin/env python3
"""Create a safe weekly note draft from verified place changes. Never publishes."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "note" / "place-snapshot.json"
OUT = ROOT / "note" / "latest"
SOURCE = ROOT / "data" / "places.json"

def run():
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    week = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    rows = json.loads(SOURCE.read_text(encoding="utf-8")).get("items", [])
    current = {}
    for p in rows:
        key = p.get("place_id")
        url = str(p.get("official_url") or "")
        if not key or not str(p.get("name") or "").strip() or not url.startswith("https://") or not p.get("sources"):
            continue
        current[key] = {"name": p["name"], "municipality": p.get("municipality", ""), "official_url": url, "address": p.get("address", "")}
    OUT.mkdir(parents=True, exist_ok=True)
    previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    changed = []
    if previous is not None:
        for key, p in current.items():
            if key not in previous:
                changed.append(("掲載施設の追加", p))
            elif p != previous[key]:
                changed.append(("掲載情報の変更", p))
    # Absence may be an acquisition error. Do not claim closure/removal.
    ready = bool(changed) and bool(os.environ.get("LOCAL_GUIDE_PUBLIC_URL", "").startswith("https://"))
    title = f"はりまよりみち｜地域情報の更新まとめ（{week}）"
    manifest = {
        "schema_version": 1, "site_id": "local", "issue_key": week,
        "status": "ready" if ready else "skip", "title": title,
        "article_path": "article.md", "cover_path": None,
        "source_url": os.environ.get("LOCAL_GUIDE_PUBLIC_URL") if ready else None,
        "generated_at": now.isoformat()
    }
    if ready:
        lines = [f"# {title}", "", "公式資料から確認できた掲載施設情報の更新をまとめました。", ""]
        for label, p in changed:
            lines += [f"## {label}：{p['name']}", f"地域：{p['municipality']}", f"所在地：{p['address'] or '未確認'}", f"施設の公式ページ：{p['official_url']}", ""]
        lines += ["掲載情報の更新であり、イベント開催や新規オープンを意味しません。最新情報は公式ページをご確認ください。", "", f"地域情報サイト：{manifest['source_url']}"]
        (OUT / "article.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Snapshot is advanced on skip as well, so initial baseline is never published as new.
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{manifest['status']}: {len(changed)} changed places")

if __name__ == "__main__":
    run()
