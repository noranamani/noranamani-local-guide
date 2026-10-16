"""Synthetic fixtures stay in temporary directories; tests never contact official sites."""
import copy
import io
import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from localguide.__main__ import main
from localguide.core import GuideError, active_occurrences, atomic_json, parse_time, read_json, safe_url, workspace_lock
from localguide.normalize import csv_records, merge_events
from localguide.site import build, event_file, validate_site
from localguide.sources import AccessStopped, MAX_BYTES, NoRedirect, approved, collect, fetch
from localguide.validation import validate_data

REPO = Path(__file__).resolve().parent.parent
NOW = parse_time("2026-10-14T16:00:00+09:00")


def fixture_source(sid="fixture_csv"):
    return {"id": sid, "label": "テスト専用の架空情報源", "area": "kakogawa", "organization_type": "organizer",
            "kind": "event_csv", "url": "https://example.com/events.csv", "enabled": True,
            "robots_review_status": "allowed", "terms_review_status": "allowed", "reuse_rights_status": "allowed",
            "attribution_required": True, "policy_url": "https://example.com/policy",
            "permission_document": "https://example.com/license", "checked_at": NOW.isoformat(),
            "robots_url": "https://example.com/robots.txt", "robots_rules": "User-agent: *\nAllow: /\n",
            "maximum_requests_per_day": 1, "adapter": "event_csv", "content_scope": "factual_metadata_only",
            "privacy_review_status": "allowed", "free_value_reviewed": True,
            "field_map": {k: k for k in ("source_event_id", "title", "municipality", "official_url", "start_at", "end_at",
                                         "status", "location_label", "price_type", "source_published_at", "organizer_label")}}


def csv_fixture(event_id="1", title="架空のテスト開催", start="2026-10-17T10:00:00+09:00", end="2026-10-17T12:00:00+09:00", price="unknown"):
    import csv
    output = io.StringIO()
    fields = list(fixture_source()["field_map"])
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerow({"source_event_id": event_id, "title": title, "municipality": "加古川市", "official_url": "https://example.com/event/" + event_id,
                     "start_at": start, "end_at": end, "status": "scheduled", "location_label": "架空の公共テスト会場",
                     "price_type": price, "source_published_at": "2026-10-13T10:00:00+09:00", "organizer_label": "架空の主催者"})
    return output.getvalue().encode()


def fixture_event(source=None, **kwargs):
    return csv_records(csv_fixture(**kwargs), source or fixture_source(), NOW.isoformat())[0]


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for directory in ("config", "data", "schemas"):
            shutil.copytree(REPO / directory, self.root / directory)
        atomic_json(self.root / "config/sources.json", {"schema_version": 1, "retrieval_is_disabled_until_review": True, "sources": [fixture_source()]})
        atomic_json(self.root / "data/source_state.json", {"schema_version": 1, "sources": {}})
        atomic_json(self.root / "data/places.json", {"schema_version": 1, "items": []})
        self.event = fixture_event()
        self.save_events([self.event])

    def tearDown(self):
        self.temp.cleanup()

    def save_events(self, events):
        atomic_json(self.root / "data/events.json", {"schema_version": 1, "items": events})

    def update_source(self, **values):
        config = read_json(self.root / "config/sources.json")
        config["sources"][0].update(values)
        atomic_json(self.root / "config/sources.json", config)

    def update_rules(self, **values):
        rules = read_json(self.root / "config/page_rules.json")
        rules.update(values)
        atomic_json(self.root / "config/page_rules.json", rules)


class NormalizationTests(unittest.TestCase):
    def test_unknown_price_is_not_free(self):
        event = fixture_event(price="")
        self.assertEqual(event["price_type"], "unknown")
        self.assertIsNone(event["age_info"])
        self.assertIsNone(event["reservation_required"])

    def test_published_and_fetched_are_distinct(self):
        source = fixture_event()["sources"][0]
        self.assertEqual(source["fetched_at"], NOW.isoformat())
        self.assertNotEqual(source["source_published_at"], source["fetched_at"])

    def test_source_date_without_time_is_preserved(self):
        source = fixture_source()
        del source["field_map"]["source_published_at"]
        source["source_published_date"] = "2026-08-25"
        event = csv_records(csv_fixture(), source, NOW.isoformat())[0]
        self.assertEqual(event["sources"][0]["source_published_at"], "2026-08-25")

    def test_csv_provenance_points_to_dataset_not_facility(self):
        event = fixture_event()
        self.assertEqual(event["sources"][0]["url"], "https://example.com/events.csv")
        self.assertEqual(event["official_url"], "https://example.com/event/1")

    def test_missing_dates_remain_null_and_unpublishable(self):
        event = fixture_event(start="", end="")
        self.assertIsNone(event["occurrences"][0]["start_at"])
        self.assertEqual(active_occurrences(event, NOW), [])

    def test_naive_date_time_rejected(self):
        with self.assertRaises(GuideError):
            fixture_event(start="2026-10-17T10:00:00")

    def test_inverted_occurrence_rejected(self):
        with self.assertRaises(GuideError):
            fixture_event(end="2026-10-16T12:00:00+09:00")

    def test_duplicate_source_id_rejected(self):
        body = csv_fixture()
        body += body.splitlines(keepends=True)[1]
        with self.assertRaises(GuideError):
            csv_records(body, fixture_source(), NOW.isoformat())

    def test_body_mapping_rejected(self):
        source = fixture_source()
        source["field_map"]["body"] = "title"
        with self.assertRaises(GuideError):
            csv_records(csv_fixture(), source, NOW.isoformat())

    def test_html_title_rejected(self):
        with self.assertRaises(GuideError):
            fixture_event(title="<script>bad</script>")

    def test_csv_header_drift_rejected(self):
        with self.assertRaises(GuideError):
            csv_records(b"id,article\n1,text\n", fixture_source(), NOW.isoformat())

    def test_invalid_encoding_rejected(self):
        with self.assertRaises(GuideError):
            csv_records(b"\xff", fixture_source(), NOW.isoformat())

    def test_malformed_quoted_csv_rejected(self):
        body = csv_fixture().splitlines(keepends=True)[0] + b'"unfinished\n'
        with self.assertRaises(GuideError):
            csv_records(body, fixture_source(), NOW.isoformat())

    def test_places_csv_keeps_unknown_price(self):
        source = fixture_source()
        source["adapter"] = "places_csv"
        source["field_map"] = {"source_event_id": "id", "name": "name", "municipality": "area", "official_url": "url"}
        place = csv_records('id,name,area,url\n1,架空テスト施設,加古川市,https://example.com/place/1\n'.encode(), source, NOW.isoformat())[0]
        self.assertIsNone(place["admission"])
        self.assertIsNone(place["address"])
        self.assertEqual(place["indoor_outdoor"], "unknown")

    def test_private_or_unreviewed_address_not_imported(self):
        source = fixture_source()
        source["adapter"] = "places_csv"
        source["field_map"] = {"source_event_id": "id", "name": "name", "municipality": "area", "official_url": "url", "address": "address"}
        body = 'id,name,area,url,address\n1,架空施設,加古川市,https://example.com/place/1,架空の住所\n'.encode()
        with self.assertRaises(GuideError):
            csv_records(body, source, NOW.isoformat())
        source["address_scope"] = "public_facilities_only"
        self.assertEqual(csv_records(body, source, NOW.isoformat())[0]["address"], "架空の住所")

    def test_cp932_csv_supported(self):
        source = fixture_source()
        source["encoding"] = "cp932"
        event = csv_records(csv_fixture().decode().encode('cp932'), source, NOW.isoformat())[0]
        self.assertEqual(event["title"], "架空のテスト開催")

    def test_unreviewed_free_mapping_rejected(self):
        source = fixture_source()
        source["free_value_reviewed"] = False
        with self.assertRaises(GuideError):
            csv_records(csv_fixture(price="free"), source, NOW.isoformat())

    def test_exact_cross_source_match_merges_provenance(self):
        first = fixture_event()
        second = fixture_event(fixture_source("fixture_two"), title="架空のテスト開催！")
        events, review = merge_events([first], [second])
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]["sources"]), 2)
        self.assertEqual(review, [])

    def test_different_date_is_held_without_merge(self):
        second = fixture_event(fixture_source("fixture_two"), start="2026-10-18T10:00:00+09:00", end="2026-10-18T12:00:00+09:00")
        events, review = merge_events([fixture_event()], [second])
        self.assertEqual(len(events), 2)
        self.assertEqual(len(review), 1)
        self.assertTrue(all(e["status"] == "unconfirmed" and e["review_hold"] for e in events))

    def test_different_venue_is_held(self):
        second = fixture_event(fixture_source("fixture_two"))
        second["location_label"] = "別の会場"
        events, review = merge_events([fixture_event()], [second])
        self.assertEqual(len(events), 2)
        self.assertTrue(review)

    def test_conflicting_price_is_held(self):
        second = fixture_event(fixture_source("fixture_two"), price="paid")
        events, review = merge_events([fixture_event()], [second])
        self.assertEqual(len(events), 2)
        self.assertTrue(review)

    def test_same_source_refresh_keeps_first_seen_and_hold(self):
        first = fixture_event()
        first.update(first_seen_at="2026-10-12T10:00:00+09:00", review_hold=True, status="unconfirmed")
        events, _ = merge_events([first], [fixture_event()])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["first_seen_at"], first["first_seen_at"])
        self.assertTrue(events[0]["review_hold"])
        self.assertEqual(events[0]["status"], "unconfirmed")

    def test_merged_event_cancellation_holds_without_duplicate_id(self):
        first = fixture_event()
        second = fixture_event(fixture_source("fixture_two"))
        merged, _ = merge_events([first], [second])
        cancelled = fixture_event()
        cancelled["status"] = "cancelled"
        events, review = merge_events(merged, [cancelled])
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["review_hold"])
        self.assertEqual(active_occurrences(events[0], NOW), [])
        self.assertEqual(review[0]["incoming"]["sources"][0]["source_id"], "fixture_csv")

    def test_date_only_preserved_with_jst_day_boundary(self):
        event = fixture_event(start="2026-10-14", end="")
        self.assertEqual(event["occurrences"][0]["start_at"], "2026-10-14")
        self.assertTrue(active_occurrences(event, parse_time("2026-10-14T23:59:59+09:00")))
        self.assertFalse(active_occurrences(event, parse_time("2026-10-15T00:00:00+09:00")))

    def test_multiple_occurrences_only_future_retained(self):
        event = fixture_event(start="2026-10-12T10:00:00+09:00", end="2026-10-12T12:00:00+09:00")
        future = fixture_event()["occurrences"][0]
        event["occurrences"].append(future)
        self.assertEqual(active_occurrences(event, NOW), [future])

    def test_cancelled_and_postponed_excluded(self):
        for status in ("cancelled", "postponed", "ended", "unconfirmed"):
            with self.subTest(status=status):
                event = fixture_event()
                event["status"] = status
                self.assertEqual(active_occurrences(event, NOW), [])


class ValidationTests(Workspace):
    def test_valid_fixture(self):
        self.assertEqual(len(validate_data(self.root, NOW)), 8)

    def test_unknown_source_rejected(self):
        self.event["sources"][0]["source_id"] = "unknown"
        self.save_events([self.event])
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_unknown_area_rejected(self):
        self.event["municipality"] = "未登録市"
        self.save_events([self.event])
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_schema_missing_fact_rejected(self):
        del self.event["price_type"]
        self.save_events([self.event])
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_duplicate_ids_rejected(self):
        self.save_events([self.event, self.event])
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_secret_detection_does_not_echo_value(self):
        secret = "ghp_" + "a" * 36
        self.event["title"] = secret
        self.save_events([self.event])
        with self.assertRaises(GuideError) as raised:
            validate_data(self.root, NOW)
        self.assertNotIn(secret, str(raised.exception))

    def test_future_verification_rejected(self):
        self.event["last_verified_at"] = (NOW + timedelta(hours=1)).isoformat()
        self.save_events([self.event])
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_unsupported_or_unsafe_urls_rejected(self):
        for url in ("javascript:alert(1)", "http://example.com", "https://a:b@example.com", "https://127.0.0.1/", "https://example.com/?token=abc"):
            with self.subTest(url=url), self.assertRaises(GuideError):
                safe_url(url)

    def test_robots_denial_and_stale_review_rejected(self):
        source = fixture_source()
        source["robots_rules"] = "User-agent: *\nDisallow: /\n"
        with self.assertRaises(GuideError):
            approved(source, NOW)
        source = fixture_source()
        source["checked_at"] = (NOW - timedelta(days=31)).isoformat()
        with self.assertRaises(GuideError):
            approved(source, NOW)

    def test_rights_and_privacy_unreviewed_rejected(self):
        for key in ("terms_review_status", "reuse_rights_status", "privacy_review_status"):
            source = fixture_source()
            source[key] = "unverified"
            with self.subTest(key=key), self.assertRaises(GuideError):
                approved(source, NOW)

    def test_robots_404_allowed_only_with_license_and_explicit_absence(self):
        source = fixture_source()
        source.update(robots_http_status=404, robots_rules="")
        approved(source, NOW)
        source["reuse_rights_status"] = "unverified"
        with self.assertRaises(GuideError):
            approved(source, NOW)
        source["reuse_rights_status"] = "allowed"
        source["robots_http_status"] = 403
        with self.assertRaises(GuideError):
            approved(source, NOW)

    def test_broken_editorial_reference_rejected(self):
        data = read_json(self.root / "data/editorial.json")
        data["featured_event_ids"] = ["not-an-event"]
        atomic_json(self.root / "data/editorial.json", data)
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)

    def test_thin_page_threshold_cannot_be_lowered(self):
        rules = read_json(self.root / "config/page_rules.json")
        rules["list_pages"]["min_active_items"] = 1
        atomic_json(self.root / "config/page_rules.json", rules)
        with self.assertRaises(GuideError):
            validate_data(self.root, NOW)


class CollectionTests(Workspace):
    def test_disabled_source_never_calls_network(self):
        self.update_source(enabled=False)
        called = []
        summaries, failures = collect(self.root, NOW, lambda *args: called.append(args))
        self.assertEqual(called, [])
        self.assertFalse(failures)
        self.assertIn("0件", summaries[0])

    def test_success_and_daily_limit(self):
        called = []
        def acquire(source, previous):
            called.append(previous)
            return csv_fixture(), {"etag": '"fixture-v1"', "last_modified": "Wed, 14 Oct 2026 07:00:00 GMT"}
        self.assertFalse(collect(self.root, NOW, acquire)[1])
        self.assertFalse(collect(self.root, NOW, acquire)[1])
        self.assertEqual(len(called), 1)
        state = read_json(self.root / "data/source_state.json")["sources"]["fixture_csv"]
        self.assertEqual(state["etag"], '"fixture-v1"')
        self.assertEqual(state["attempts"], 1)

    def test_fetch_failure_retains_data_and_expired_does_not_reappear(self):
        self.event["occurrences"][0].update(start_at="2026-10-12T10:00:00+09:00", end_at="2026-10-12T12:00:00+09:00")
        self.save_events([self.event])
        before = (self.root / "data/events.json").read_bytes()
        def failed(*args):
            raise GuideError("接続失敗")
        _, failures = collect(self.root, NOW, failed)
        self.assertTrue(failures)
        self.assertEqual(before, (self.root / "data/events.json").read_bytes())
        self.assertEqual(build(self.root, NOW)["events"], 0)

    def test_access_denial_halts_future_requests(self):
        count = []
        def denied(*args):
            count.append(1)
            raise AccessStopped("HTTP 429: 停止")
        self.assertTrue(collect(self.root, NOW, denied)[1])
        self.assertTrue(collect(self.root, NOW + timedelta(days=1), denied)[1])
        self.assertEqual(len(count), 1)
        self.assertTrue(read_json(self.root / "data/source_state.json")["sources"]["fixture_csv"]["halted"])

    def test_304_refreshes_verification_not_acquisition_or_publication(self):
        self.assertFalse(collect(self.root, NOW, lambda *a: (csv_fixture(), {"etag": '"v1"'}))[1])
        before = read_json(self.root / "data/events.json")["items"][0]
        next_day = NOW + timedelta(days=1)
        self.assertFalse(collect(self.root, next_day, lambda *a: (None, {}))[1])
        after = read_json(self.root / "data/events.json")["items"][0]
        self.assertEqual(before["sources"][0]["fetched_at"], after["sources"][0]["fetched_at"])
        self.assertEqual(before["sources"][0]["source_published_at"], after["sources"][0]["source_published_at"])
        self.assertEqual(after["sources"][0]["last_checked_at"], next_day.isoformat())
        self.assertEqual(after["last_verified_at"], next_day.isoformat())

    def test_first_request_304_without_cached_success_rejected(self):
        before = (self.root / "data/events.json").read_bytes()
        self.assertTrue(collect(self.root, NOW, lambda *a: (None, {}))[1])
        self.assertEqual(before, (self.root / "data/events.json").read_bytes())

    def test_mass_data_drop_keeps_last_data(self):
        before = (self.root / "data/events.json").read_bytes()
        empty = csv_fixture().splitlines(keepends=True)[0]
        self.assertTrue(collect(self.root, NOW, lambda *a: (empty, {}))[1])
        self.assertEqual(before, (self.root / "data/events.json").read_bytes())

    def test_invalid_response_keeps_last_data(self):
        before = (self.root / "data/events.json").read_bytes()
        self.assertTrue(collect(self.root, NOW, lambda *a: (b"not,csv\n", {}))[1])
        self.assertEqual(before, (self.root / "data/events.json").read_bytes())

    def test_conditional_headers_timeout_and_tls_route(self):
        class Headers:
            def get_content_type(self): return "text/csv"
            def get(self, key): return '"fixture"' if key == "ETag" else None
        class Response:
            headers = Headers()
            def read(self, size): self.size = size; return csv_fixture()
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with patch("localguide.sources.build_opener") as factory:
            opener = factory.return_value
            opener.open.return_value = Response()
            body, headers = fetch(fixture_source(), {"etag": '"old"', "last_modified": "Wed, 14 Oct 2026 07:00:00 GMT"})
            request = opener.open.call_args.args[0]
            self.assertEqual(request.get_header("If-none-match"), '"old"')
            self.assertEqual(opener.open.call_args.kwargs["timeout"], 20)
            self.assertEqual(headers["etag"], '"fixture"')
            self.assertTrue(body)

    def test_redirect_never_followed(self):
        with self.assertRaises(GuideError):
            NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://other.example.org")

    def test_http_denial_no_body_logged(self):
        for code in (401, 403, 429):
            with self.subTest(code=code), patch("localguide.sources.build_opener") as factory:
                factory.return_value.open.side_effect = HTTPError("https://example.com", code, "SECRET", {}, None)
                with self.assertRaises(AccessStopped) as raised:
                    fetch(fixture_source(), {})
                self.assertNotIn("SECRET", str(raised.exception))

    def test_network_error_and_server_error_are_safe(self):
        for error in (URLError("SECRET"), HTTPError("https://example.com", 500, "SECRET", {}, None)):
            with patch("localguide.sources.build_opener") as factory:
                factory.return_value.open.side_effect = error
                with self.assertRaises(GuideError) as raised:
                    fetch(fixture_source(), {})
                self.assertNotIn("SECRET", str(raised.exception))

    def test_304_response_handled(self):
        with patch("localguide.sources.build_opener") as factory:
            factory.return_value.open.side_effect = HTTPError("https://example.com", 304, "Not Modified", {}, None)
            self.assertEqual(fetch(fixture_source(), {}), (None, {}))

    def test_response_size_and_non_csv_rejected(self):
        class Headers:
            def __init__(self, kind): self.kind = kind
            def get_content_type(self): return self.kind
            def get(self, name): return None
        class Response:
            def __init__(self, kind, body): self.headers, self.body = Headers(kind), body
            def read(self, size): return self.body[:size]
            def __enter__(self): return self
            def __exit__(self, *args): pass
        for response in (Response("text/html", b"captcha"), Response("text/csv", b"x" * (MAX_BYTES + 1))):
            with patch("localguide.sources.build_opener") as factory:
                factory.return_value.open.return_value = response
                with self.assertRaises(GuideError):
                    fetch(fixture_source(), {})

    def test_concurrent_collection_stops_before_network(self):
        with workspace_lock(self.root):
            with self.assertRaises(GuideError):
                collect(self.root, NOW, lambda *a: self.fail("network must not be called"))


class SiteTests(Workspace):
    def test_about_is_reachable_from_every_generated_page(self):
        manifest = build(self.root, NOW)
        self.assertIn("about.html", manifest["files"])
        self.assertIn(event_file(self.event), manifest["files"])
        for name in manifest["files"]:
            if not name.endswith(".html"):
                continue
            with self.subTest(page=name):
                content = (self.root / "docs" / name).read_text(encoding="utf-8")
                header, footer = content.split('<footer class="site-footer">')
                self.assertNotIn('href="about.html"', header)
                self.assertIn('href="about.html"', footer)
                self.assertIn("このサイトについて</a>", footer)
        about = (self.root / "docs/about.html").read_text(encoding="utf-8")
        self.assertIn('href="about.html" aria-current="page"', about)
        self.assertIn('href="#main-content"', about)
        self.assertNotIn("mailto:", about)
        self.assertFalse(any(f"<{tag}" in about for tag in ("form", "script", "iframe")))
        self.assertEqual(validate_site(self.root / "docs"), manifest)

    def test_about_does_not_add_indexable_policy_or_tracking(self):
        self.update_rules(site_url="https://example.com")
        build(self.root, NOW)
        about = (self.root / "docs/about.html").read_text(encoding="utf-8")
        self.assertIn('content="noindex,follow"', about)
        self.assertNotIn('rel="canonical"', about)
        sitemap = (self.root / "docs/sitemap.xml").read_text(encoding="utf-8")
        self.assertNotIn("about.html", sitemap)
        self.assertNotIn("beacon", about)
        validate_site(self.root / "docs", "https://example.com")

    def test_nonempty_generation_provenance_and_unknown_price(self):
        result = build(self.root, NOW)
        self.assertEqual(result["events"], 1)
        content = (self.root / "docs" / event_file(self.event)).read_text()
        self.assertIn("架空のテスト開催", content)
        self.assertIn("料金</dt><dd>不明", content)
        self.assertIn("発表日時", content)
        self.assertIn("data-source-id", content)
        self.assertEqual(validate_site(self.root / "docs")["events"], 1)

    def test_empty_site_no_fake_events_or_seo(self):
        self.save_events([])
        result = build(self.root, NOW)
        self.assertEqual(result["events"], 0)
        self.assertFalse((self.root / "docs/events.html").exists())
        index = (self.root / "docs/index.html").read_text()
        self.assertIn("掲載準備中", index)
        self.assertIn('content="noindex,follow"', index)
        self.assertNotIn('rel="canonical"', index)
        self.assertFalse((self.root / "docs/sitemap.xml").exists())
        self.assertFalse((self.root / "docs/robots.txt").exists())

    def test_expired_and_cancelled_excluded(self):
        old = fixture_event(event_id="2", title="終了テスト", start="2026-10-12T10:00:00+09:00", end="2026-10-12T12:00:00+09:00")
        cancelled = fixture_event(event_id="3", title="中止テスト")
        cancelled["status"] = "cancelled"
        self.save_events([self.event, old, cancelled])
        self.assertEqual(build(self.root, NOW)["events"], 1)
        index = (self.root / "docs/index.html").read_text()
        self.assertNotIn("終了テスト", index)
        self.assertNotIn("中止テスト", index)

    def test_stale_hidden(self):
        self.assertEqual(build(self.root, NOW + timedelta(hours=73))["events"], 0)

    def test_disabled_source_hidden(self):
        self.update_source(enabled=False)
        self.assertEqual(build(self.root, NOW)["events"], 0)

    def test_places_collection_and_generation(self):
        source = fixture_source()
        source["adapter"] = "places_csv"
        source["field_map"] = {"source_event_id": "id", "name": "name", "municipality": "area", "official_url": "url"}
        self.update_source(**source)
        self.save_events([])
        body = 'id,name,area,url\n1,架空テスト施設,加古川市,https://example.com/place/1\n'.encode()
        self.assertFalse(collect(self.root, NOW, lambda *a: (body, {}))[1])
        result = build(self.root, NOW)
        self.assertEqual(result["places"], 1)
        index = (self.root / "docs/index.html").read_text()
        self.assertIn("架空テスト施設", index)
        self.assertIn("料金：不明", index)
        self.assertIn('data-source-id="fixture_csv"', index)

    def test_small_groups_not_generated(self):
        result = build(self.root, NOW)
        self.assertFalse(any(f.startswith(("area-", "category-")) for f in result["files"]))

    def test_category_activation_requires_continuous_week_and_organizers(self):
        events = [fixture_event(event_id=str(i), title=f"架空テスト{i}", start="2026-11-01T10:00:00+09:00", end="2026-11-01T12:00:00+09:00") for i in range(5)]
        for i, event in enumerate(events):
            event["organizer_label"] = f"架空主催者{i % 2}"
        self.save_events(events)
        self.assertNotIn("area-kakogawa.html", build(self.root, NOW)["files"])
        for day in range(1, 8):
            day_now = NOW + timedelta(days=day)
            for event in events:
                event["last_verified_at"] = day_now.isoformat()
                event["sources"][0]["fetched_at"] = day_now.isoformat()
                event["sources"][0]["last_checked_at"] = day_now.isoformat()
            self.save_events(events)
            result = build(self.root, day_now)
        self.assertIn("area-kakogawa.html", result["files"])
        self.assertIn("category-event.html", result["files"])

    def test_failed_build_preserves_previous_site(self):
        build(self.root, NOW)
        before = {p.name: p.read_bytes() for p in (self.root / "docs").iterdir()}
        self.event["occurrences"][0]["end_at"] = "2026-10-10T12:00:00+09:00"
        self.save_events([self.event])
        with self.assertRaises(GuideError):
            build(self.root, NOW)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / "docs").iterdir()})

    def test_validation_failure_in_staging_preserves_previous_site(self):
        build(self.root, NOW)
        before = (self.root / "docs/index.html").read_bytes()
        with patch("localguide.site.validate_site", side_effect=GuideError("fixture failure")):
            with self.assertRaises(GuideError):
                build(self.root, NOW)
        self.assertEqual(before, (self.root / "docs/index.html").read_bytes())

    def test_state_write_failure_preserves_previous_site(self):
        build(self.root, NOW)
        before = (self.root / "docs/index.html").read_bytes()
        with patch("localguide.site.atomic_json", side_effect=OSError("fixture I/O failure")):
            with self.assertRaises(OSError):
                build(self.root, NOW)
        self.assertEqual(before, (self.root / "docs/index.html").read_bytes())

    def test_replace_failure_restores_backup(self):
        import os
        build(self.root, NOW)
        before = (self.root / "docs/index.html").read_bytes()
        original = os.replace
        def replace(source, destination):
            if Path(source).name.startswith(".guide-build-"):
                raise OSError("fixture rename failure")
            return original(source, destination)
        with patch("localguide.site.os.replace", side_effect=replace):
            with self.assertRaises(OSError):
                build(self.root, NOW)
        self.assertEqual(before, (self.root / "docs/index.html").read_bytes())

    def test_unknown_docs_files_not_overwritten(self):
        (self.root / "docs").mkdir()
        (self.root / "docs/custom.txt").write_text("user content")
        with self.assertRaises(GuideError):
            build(self.root, NOW)
        self.assertEqual((self.root / "docs/custom.txt").read_text(), "user content")

    def test_repeat_build_same_inputs_same_outputs(self):
        build(self.root, NOW)
        first = {p.name: p.read_bytes() for p in (self.root / "docs").iterdir()}
        build(self.root, NOW)
        self.assertEqual(first, {p.name: p.read_bytes() for p in (self.root / "docs").iterdir()})

    def test_site_url_sitemap_only_indexable(self):
        self.update_rules(site_url="https://example.com/local-guide")
        build(self.root, NOW)
        self.assertTrue((self.root / "docs/sitemap.xml").exists())
        sitemap = (self.root / "docs/sitemap.xml").read_text()
        self.assertIn(event_file(self.event), sitemap)
        self.assertNotIn("index.html", sitemap)
        self.assertIn("Sitemap: https://example.com/local-guide/sitemap.xml", (self.root / "docs/robots.txt").read_text())
        self.assertEqual(validate_site(self.root / "docs", "https://example.com/local-guide")["events"], 1)

    def test_broken_local_link_rejected(self):
        build(self.root, NOW)
        path = self.root / "docs/index.html"
        path.write_text(path.read_text().replace('href="events.html"', 'href="missing.html"'))
        with self.assertRaises(GuideError):
            validate_site(self.root / "docs")

    def test_script_injection_rejected(self):
        build(self.root, NOW)
        path = self.root / "docs/index.html"
        path.write_text(path.read_text().replace("</main>", "<script>alert(1)</script></main>"))
        with self.assertRaises(GuideError):
            validate_site(self.root / "docs")

    def test_provenance_removal_rejected(self):
        build(self.root, NOW)
        path = self.root / "docs" / event_file(self.event)
        path.write_text(path.read_text().replace("data-source-id", "data-removed-id"))
        with self.assertRaises(GuideError):
            validate_site(self.root / "docs")

    def test_cli_invalid_data_nonzero_and_run_stops(self):
        self.update_source(terms_review_status="unverified")
        with patch("sys.stderr", new=io.StringIO()):
            self.assertEqual(main(["run", "--root", str(self.root), "--now", NOW.isoformat()]), 1)
        self.assertFalse((self.root / "docs").exists())


if __name__ == "__main__":
    unittest.main()
