"""Shared I/O, date and URL rules. No credentials or third-party text are stored."""
import json
import os
import re
import tempfile
from contextlib import contextmanager
from functools import wraps
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


class GuideError(ValueError):
    pass


def now_jst():
    return datetime.now(JST)


def parse_time(value):
    if not isinstance(value, str):
        raise GuideError("日時はISO8601文字列で指定してください")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GuideError("日時の形式が不正です") from exc
    if result.tzinfo is None:
        raise GuideError("日時にはタイムゾーンが必要です")
    return result.astimezone(JST)


def parse_fact_time(value):
    """Use day bounds only for comparisons; keep date-only source facts unchanged."""
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.combine(date.fromisoformat(value), time.min, JST)
    return parse_time(value)


def occurrence_bounds(occurrence):
    """Date-only facts remain date-only in data and presentation."""
    start, end = occurrence["start_at"], occurrence["end_at"]
    if start is None:
        if end is not None:
            raise GuideError("開始不明の開催回に終了日時だけを指定できません")
        return None, None

    def bound(value, is_end=False):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.combine(date.fromisoformat(value), time.max if is_end else time.min, JST)
        return parse_time(value)

    first = bound(start)
    # Unknown end times are never fabricated; conservatively remove after start.
    last = bound(end, True) if end else (bound(start, True) if len(start) == 10 else first)
    if last < first:
        raise GuideError("開催回の終了が開始より前です")
    return first, last


def safe_url(url):
    if not isinstance(url, str):
        raise GuideError("URLは文字列で指定してください")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise GuideError("URLの形式が不正です") from exc
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or port not in (None, 443) or parts.fragment or any(c.isspace() for c in url)
            or parts.hostname == "localhost" or "." not in parts.hostname
            or re.fullmatch(r"[\d.]+", parts.hostname)):
        raise GuideError("公開HTTPS URLのみ使用できます（認証情報・IP・断片は禁止）")
    if parts.query:
        if re.search(r"(?i)(token|secret|password|api[_-]?key|signature|credential)", parts.query):
            raise GuideError("秘密値を含む可能性のあるURLです")
    return url


def read_json(path):
    def reject_constant(value):
        raise ValueError("Non-finite JSON number")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=reject_constant)
    except (ValueError, OSError) as exc:
        raise GuideError(f"JSONを読み込めません: {Path(path).name}") from exc


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".guide-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def active_occurrences(event, now):
    if event["status"] not in ("scheduled",):
        return []
    return [o for o in event["occurrences"]
            if o["status"] == "scheduled" and occurrence_bounds(o)[1] is not None
            and occurrence_bounds(o)[1] >= now]


@contextmanager
def workspace_lock(root):
    """Prevent overlapping local collection/build jobs from violating limits."""
    import fcntl
    path = Path(root) / "cache/pipeline.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise GuideError("別の取得・生成処理が実行中です。競合を避けて停止します") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def serialized(function):
    @wraps(function)
    def wrapper(root, *args, **kwargs):
        with workspace_lock(root):
            return function(root, *args, **kwargs)
    return wrapper
