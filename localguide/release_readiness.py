"""Offline release-readiness report; never a deployment authorization."""
from pathlib import Path

from .core import active_occurrences
from .page_places import qualified_places
from .site import qualified, validate_site
from .validation import publishable, validate_config, validate_data


MANUAL_CHECKS = (
    ("問い合わせ窓口（任意）", "初期公開の必須条件ではない。誤掲載対応用に設ける場合も私用メールを公開しない"),
    ("個人情報・広告・販売要件（導入時に確認）", "個人データ収集・広告・自サイト販売の実施内容に応じて法令・規約を確認する"),
    ("スマホとPCの実機レビュー", "表示・出典・料金・イベント条件・公式リンクを確認"),
    ("Cloudflare初回デプロイの承認", "pages.devは公開URLになるため所有者の明示承認が必要"),
)


def assess(root, now):
    """Read verified local data and compiled docs; never call a remote service."""
    root = Path(root).resolve()
    data = validate_data(root, now)
    _, _, rules, registry = validate_config(root, now)
    manifest = validate_site(root / "docs", rules["site_url"])
    sources = {s["id"]: s for s in registry["sources"]}
    stale = rules["review"]["stale_event_after_hours"]
    events = [e for e in data["events"]["items"] if active_occurrences(e, now)
              and publishable(e, sources, now, stale)]
    places = [p for p in data["places"]["items"] if publishable(p, sources, now, stale)]
    event_sources = {s["source_id"] for e in events for s in e["sources"] if s["is_primary"]}
    official_events = sum(any(s["is_primary"] for s in e["sources"]) for e in events)
    organizers = len({e.get("organizer_label") for e in events if e.get("organizer_label")})
    html_names = [name for name in manifest["files"] if name.endswith(".html")]
    page_bodies = [(root / "docs" / name).read_text(encoding="utf-8") for name in html_names]
    searchable = sum('content="index,follow"' in body for body in page_bodies)
    header_path = root / "docs/_headers"
    if "_headers" not in manifest["files"] or not header_path.is_file():
        raise ValueError("Cloudflareのヘッダーが見つかりません")
    xrobots_noindex = "X-Robots-Tag: noindex" in header_path.read_text(encoding="utf-8")
    safe_draft = (searchable == 0 and xrobots_noindex
                  and all('content="noindex,follow"' in body for body in page_bodies))
    if rules["site_url"] is None and not safe_draft:
        raise ValueError("公開URL未設定のHTMLからnoindexが欠落しています")
    return {
        "generated_at": now.isoformat(),
        "site_url": rules["site_url"],
        "html_pages": len(html_names),
        "indexable_pages": searchable,
        "draft_noindex": safe_draft,
        "events": len(events),
        "events_min": rules["list_pages"]["min_active_items"],
        "official_events": official_events,
        "official_events_min": rules["list_pages"]["min_official_items"],
        "organizers": organizers,
        "organizers_min": rules["list_pages"]["min_distinct_organizers"],
        "event_primary_sources": len(event_sources),
        "events_pass": qualified(events, rules),
        "places": len(places),
        "places_min": rules["place_pages"]["min_places"],
        "places_pass": qualified_places(places, rules["place_pages"]),
        "sources_enabled": sum(s["enabled"] for s in registry["sources"]),
        "sources_total": len(registry["sources"]),
        "manual_checks": MANUAL_CHECKS,
        "publication_approved": False,
    }


def markdown_report(report):
    def status(is_good):
        return "達成" if is_good else "未達"

    rows = [
        ("生成済みHTMLの検証", "達成", f"{report['html_pages']}ページを検証"),
        ("SEO保護・ヘッダー", status(report["draft_noindex"] or report["indexable_pages"] > 0),
         f"検索対象{report['indexable_pages']}ページ、公開前noindex={'あり' if report['draft_noindex'] else '対象外'}"),
        ("今後のイベント情報", status(report["events_pass"]),
         f"確認済み{report['events']}件／目標{report['events_min']}件、一次情報{report['official_events']}件"
         f"／目標{report['official_events_min']}件、主催者{report['organizers']}者／目標{report['organizers_min']}者"),
        ("イベントの一次情報源", status(report["event_primary_sources"] > 0),
         f"確認済み{report['event_primary_sources']}件"),
        ("一般利用できる施設の品質", status(report["places_pass"]),
         f"確認済み{report['places']}件／目標{report['places_min']}件（公式出典・異なる公式サイトも必要）"),
        ("公開URL", status(bool(report["site_url"])),
         "URL設定あり。配信中かどうかは別途確認" if report["site_url"] else "site_url未設定"),
    ]
    lines = [
        "# はりまよりみち — 公開前の自動点検（未公開）", "",
        f"点検日時：{report['generated_at']}", "",
        "**公開判定：保留。** 自動チェックが成功しても公開許可にはなりません。",
        "このチェックは外部アクセス、メール送信、課金、Cloudflare接続、デプロイを行いません。",
        "", "| 点検項目 | 結果 | 根拠 |", "|---|---|---|"
    ]
    lines += [f"| {item} | {result} | {detail} |" for item, result, detail in rows]
    lines += ["", f"有効情報源：{report['sources_enabled']} / {report['sources_total']}件。"
              " 情報源の有効化とイベント開催情報の取得許可は別に確認します。",
              "", "## 人による確認・任意項目（すべてが公開の必須条件ではありません）"]
    lines += [f"- [ ] **{title}**：{detail}" for title, detail in report["manual_checks"]]
    lines += [
        "", "※ noindexは検索エンジン向けで、ページへの一般アクセスを制限しません。",
        "※ 初回Cloudflareデプロイはユーザーの明示承認が必要です。", ""
    ]
    return "\n".join(lines)
