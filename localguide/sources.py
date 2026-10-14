"""Reviewed HTTPS CSV acquisition with conditional requests and durable limits."""
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .core import GuideError, atomic_json, parse_time, read_json, safe_url, serialized
from .normalize import csv_records, merge_events

USER_AGENT = "noranamani-local-guide/0.1"
MAX_BYTES = 2 * 1024 * 1024


def approved(source, now):
    if not source.get("enabled"):
        raise GuideError("無効な情報源です")
    for key in ("robots_review_status", "terms_review_status", "reuse_rights_status"):
        if source.get(key) != "allowed":
            raise GuideError(f"情報源の審査が未完了です: {key}")
    for key in ("url", "policy_url", "permission_document", "robots_url"):
        safe_url(source.get(key))
    if source.get("attribution_required") is not True:
        raise GuideError("出典表示条件の明示が必要です")
    if source.get("content_scope") != "factual_metadata_only" or source.get("privacy_review_status") != "allowed":
        raise GuideError("事実列の利用範囲と個人情報除外の審査が必要です")
    checked = parse_time(source.get("checked_at"))
    if checked > now or now - checked > timedelta(days=30):
        raise GuideError("情報源の審査は30日以内の再確認が必要です")
    if source.get("adapter") not in ("event_csv", "places_csv") or not isinstance(source.get("field_map"), dict):
        raise GuideError("対応する審査済みCSVマッピングがありません")
    rules = source.get("robots_rules")
    if source.get("robots_http_status") == 404 and rules == "":
        # RFC 9309 section 2.3.1.3: absence of robots is not a reuse permission.
        # Terms/license/privacy approval above is still mandatory.
        pass
    elif isinstance(rules, str) and rules.strip():
        robots = RobotFileParser()
        robots.parse(rules.splitlines())
        if not robots.can_fetch(USER_AGENT, source["url"]):
            raise GuideError("robotsルールが取得を許可していません")
    else:
        raise GuideError("審査したrobotsルールまたは404の記録がありません")
    if urlsplit(source["robots_url"]).hostname != urlsplit(source["url"]).hostname:
        raise GuideError("robots審査の対象ホストが一致しません")
    limit = source.get("maximum_requests_per_day")
    if type(limit) is not int or not 1 <= limit <= 10:
        raise GuideError("1〜10回の日次取得上限が必要です")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise GuideError("未審査のリダイレクトは停止します。移動先を再審査してください")


def fetch(source, previous):
    headers = {"User-Agent": USER_AGENT, "Accept": "text/csv, application/csv", "Accept-Encoding": "identity"}
    for state_key, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
        value = previous.get(state_key)
        if value:
            if len(value) > 1024 or "\r" in value or "\n" in value:
                raise GuideError("条件付き取得ヘッダーが不正です")
            headers[header] = value
    opener = build_opener(NoRedirect())
    try:
        with opener.open(Request(safe_url(source["url"]), headers=headers), timeout=20) as response:
            kind = response.headers.get_content_type()
            if kind not in ("text/csv", "application/csv", "application/octet-stream", "text/plain", "application/vnd.ms-excel"):
                raise GuideError("CSV以外のレスポンスです。ログイン・CAPTCHA・HTMLは処理しません")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise GuideError("CSVが取得サイズ上限を超えました")
            validators = {"etag": response.headers.get("ETag"), "last_modified": response.headers.get("Last-Modified")}
            if any(value and (len(value) > 1024 or "\r" in value or "\n" in value) for value in validators.values()):
                raise GuideError("応答の条件付き取得ヘッダーが不正です")
            return body, validators
    except HTTPError as exc:
        if exc.code == 304:
            return None, {}
        if exc.code in (401, 403, 429):
            raise AccessStopped(f"HTTP {exc.code}: 取得を停止。許可・頻度を再審査してください") from None
        raise GuideError(f"HTTP {exc.code}: 前回データを保持します") from None
    except (URLError, TimeoutError, OSError):
        # Do not echo URLs, proxy details, or response bodies into logs.
        raise GuideError("接続失敗: 前回データを保持します") from None


class AccessStopped(GuideError):
    pass


@serialized
def collect(root, now, fetcher=fetch):
    from .validation import validate_data, validate_dataset
    validate_data(root, now)
    sources = read_json(root / "config/sources.json")["sources"]
    state_path = root / "data/source_state.json"
    state = read_json(state_path)
    failures, summaries = [], []
    for source in sources:
        if not source["enabled"]:
            continue
        sid = source["id"]
        previous = state["sources"].get(sid, {})
        try:
            approved(source, now)
            if previous.get("halted"):
                raise GuideError("アクセス拒否による停止中です。手動再審査が必要です")
            same_day = previous.get("attempt_day") == now.date().isoformat()
            attempts = previous.get("attempts", 0) if same_day else 0
            if attempts >= source["maximum_requests_per_day"]:
                summaries.append(f"{sid}: 日次上限のため取得省略")
                continue
            attempt = {**previous, "attempt_day": now.date().isoformat(), "attempts": attempts + 1,
                       "last_attempt_at": now.isoformat()}
            # Reserve the request before touching the network; failures count too.
            state["sources"][sid] = attempt
            atomic_json(state_path, state)
            body, headers = fetcher(source, previous)
            reviews = []
            if body is not None:
                incoming = csv_records(body, source, now.isoformat())
                target = "events" if source["adapter"] == "event_csv" else "places"
                dataset = read_json(root / f"data/{target}.json")
                old = [r for r in dataset["items"] if any(s["source_id"] == sid for s in r["sources"])]
                if old and len(incoming) < len(old) * 0.5:
                    raise GuideError("データ件数が前回の半分未満です。手動確認まで更新しません")
                if target == "events":
                    items, reviews = merge_events(dataset["items"], incoming)
                else:
                    ids = {p["place_id"] for p in incoming}
                    items = [p for p in dataset["items"] if p["place_id"] not in ids] + incoming
                candidate = {"schema_version": 1, "items": items}
                validate_dataset(root, target, candidate, now)
                if reviews:
                    pending = root / "cache/review_queue.json"
                    existing = read_json(pending) if pending.exists() else {"items": []}
                    existing["items"].extend(reviews)
                    atomic_json(pending, existing)
                atomic_json(root / f"data/{target}.json", candidate)
            else:
                # The server confirmed the previously validated CSV is unchanged.
                # Preserve original acquisition/publication times; refresh only verification.
                if not previous.get("last_success_at"):
                    raise GuideError("初回取得で304を受け取りました。検証済みデータがありません")
                target = "events" if source["adapter"] == "event_csv" else "places"
                dataset = read_json(root / f"data/{target}.json")
                for record in dataset["items"]:
                    if any(p["source_id"] == sid for p in record["sources"]):
                        for provenance in record["sources"]:
                            if provenance["source_id"] == sid:
                                provenance["last_checked_at"] = now.isoformat()
                        record["last_verified_at"] = min((p["last_checked_at"] for p in record["sources"]), key=parse_time)
                validate_dataset(root, target, dataset, now)
                atomic_json(root / f"data/{target}.json", dataset)
            attempt.update(headers)
            attempt.update({"last_success_at": now.isoformat(), "last_error": None, "halted": False})
            state["sources"][sid] = attempt
            summaries.append(f"{sid}: {'変更なし (304)' if body is None else str(len(incoming)) + '件を正規化'}")
        except GuideError as exc:
            current = state["sources"].get(sid, previous).copy()
            current["last_error"] = str(exc)
            if isinstance(exc, AccessStopped):
                current["halted"] = True
            state["sources"][sid] = current
            failures.append(f"{sid}: {exc}")
        atomic_json(state_path, state)
    if not any(s["enabled"] for s in sources):
        summaries.append("有効な審査済み情報源は0件です。外部取得せず既存データを保持しました")
    return summaries, failures
