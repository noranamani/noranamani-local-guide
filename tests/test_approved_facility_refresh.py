"""No-network regression tests for daily municipal-facility maintenance."""
import csv
import io
import json
import shutil
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from localguide.core import GuideError, atomic_json, parse_time, read_json
from localguide.sources import AccessStopped
from scripts.refresh_approved_places import SOURCE_ID, refresh_once

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOW = parse_time("2026-10-17T08:25:00+09:00")


class SafeScheduledFacilityRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("config", "data", "schemas"):
            shutil.copytree(PROJECT_ROOT / folder, self.root / folder)
        self.before_places = (self.root / "data/places.json").read_bytes()
        self.before_state = read_json(self.root / "data/source_state.json")
        self.calls = []

    def unchanged(self, source, previous):
        self.calls.append(source["id"])
        return None, {}

    def official_csv(self, count=4):
        places = read_json(self.root / "data/places.json")["items"]
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(("ID", "名称", "所在地_市区町村", "所在地_連結表記", "URL"))
        for place in places[:count]:
            writer.writerow((
                place["sources"][0]["source_event_id"],
                place["name"], place["municipality"],
                place["address"] or "", place["official_url"]
            ))
        return stream.getvalue().encode("utf-8-sig")

    def test_successful_304_updates_only_verification_and_attempt(self):
        before = read_json(self.root / "data/places.json")["items"][0]
        self.assertEqual(refresh_once(self.root, NOW, self.unchanged), "updated")
        after = read_json(self.root / "data/places.json")["items"][0]
        state = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        self.assertEqual(self.calls, [SOURCE_ID])
        self.assertEqual(after["last_verified_at"], NOW.isoformat())
        self.assertEqual(after["sources"][0]["fetched_at"], before["sources"][0]["fetched_at"])
        self.assertEqual(after["sources"][0]["source_published_at"],
                         before["sources"][0]["source_published_at"])
        self.assertEqual(state["last_success_at"], NOW.isoformat())
        self.assertEqual(state["attempt_day"], "2026-10-17")
        self.assertEqual(state["attempts"], 1)
        self.assertFalse(state["halted"])
        self.assertEqual(state["last_error"], None)

    def test_reviewed_csv_refresh_revalidates_and_replaces_one_source(self):
        data = self.official_csv()
        def get_csv(source, previous):
            self.calls.append(source["id"])
            return data, {"etag": '"test-v2"'}
        self.assertEqual(refresh_once(self.root, NOW, get_csv), "updated")
        places = read_json(self.root / "data/places.json")["items"]
        state = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        self.assertEqual(len(places), 4)
        self.assertEqual(self.calls, [SOURCE_ID])
        self.assertEqual(state["etag"], '"test-v2"')
        self.assertEqual({p["last_verified_at"] for p in places}, {NOW.isoformat()})

    def test_failure_never_rewrites_facility_snapshot_but_counts_request(self):
        def unavailable(source, previous):
            self.calls.append(source["id"])
            raise GuideError("Official CSV unavailable")
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, unavailable)
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)
        state = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        old = self.before_state["sources"][SOURCE_ID]
        self.assertEqual(state["last_success_at"], old["last_success_at"])
        self.assertEqual(state["etag"], old["etag"])
        self.assertEqual(state["attempts"], 1)
        self.assertEqual(state["attempt_day"], NOW.date().isoformat())
        self.assertIsNotNone(state["last_error"])
        self.assertFalse(state["halted"])
        self.assertEqual(refresh_once(self.root, NOW, self.unchanged), "skipped")
        self.assertEqual(self.calls, [SOURCE_ID])

    def test_http_access_denial_persists_halt_and_prevents_next_day_call(self):
        def blocked(source, previous):
            self.calls.append(source["id"])
            raise AccessStopped("HTTP 403")
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, blocked)
        self.assertTrue(read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]["halted"])
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW + timedelta(days=1), blocked)
        self.assertEqual(self.calls, [SOURCE_ID])
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)

    def test_bad_csv_preserves_data_and_does_not_claim_success(self):
        def wrong_header(source, previous):
            self.calls.append(source["id"])
            return b"malformed,csv\nbad,value\n", {}
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, wrong_header)
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)
        state = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        self.assertEqual(state["last_success_at"],
                         self.before_state["sources"][SOURCE_ID]["last_success_at"])
        self.assertEqual(state["attempt_day"], NOW.date().isoformat())

    def test_valid_download_rejected_by_build_cannot_claim_success(self):
        def broken_builder(root, now):
            raise GuideError("Intentional preview validation failure")
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, self.unchanged, builder=broken_builder)
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)
        after = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        self.assertEqual(after["last_success_at"],
                         self.before_state["sources"][SOURCE_ID]["last_success_at"])
        self.assertEqual(after["attempts"], 1)
        self.assertNotIn("Intentional", after["last_error"])

    def test_50_percent_drop_requires_manual_review(self):
        data = self.official_csv(count=2)
        def suspicious(source, previous):
            return data, {}
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, suspicious)
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)
        state = read_json(self.root / "data/source_state.json")["sources"][SOURCE_ID]
        self.assertEqual(state["attempts"], 1)
        self.assertEqual(state["last_success_at"],
                         self.before_state["sources"][SOURCE_ID]["last_success_at"])

    def test_other_enabled_source_is_never_called(self):
        registry = read_json(self.root / "config/sources.json")
        other = next(item for item in registry["sources"] if not item["enabled"])
        other["enabled"] = True
        atomic_json(self.root / "config/sources.json", registry)
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW, self.unchanged)
        self.assertEqual(self.calls, [])
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)

    def test_expired_rights_review_never_fetches(self):
        with self.assertRaises(GuideError):
            refresh_once(self.root, NOW + timedelta(days=33), self.unchanged)
        self.assertEqual(self.calls, [])
        self.assertEqual((self.root / "data/places.json").read_bytes(), self.before_places)

    def test_workflow_only_commits_allowlisted_files_and_limits_schedule(self):
        path = PROJECT_ROOT / ".github/workflows/refresh-approved-places.yml"
        workflow = path.read_text(encoding="utf-8")
        self.assertIn("cron: '25 23 * * *'", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("git add -- data/source_state.json", workflow)
        self.assertIn("git add -- data/places.json", workflow)
        self.assertIn("if [ \"$REFRESH_OUTCOME\" = \"success\" ]; then", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        self.assertNotIn("git push --force", workflow)
        self.assertNotIn("wrangler pages deploy", workflow)


if __name__ == "__main__":
    unittest.main()
