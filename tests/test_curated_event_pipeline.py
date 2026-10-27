"""Synthetic-only tests for owner approval, publication gates and offline retirement."""
import copy
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from localguide.core import GuideError, now_jst, read_json
from localguide.curated_events import (
    _validate_events, curated_event_cards, event_state, public_curated_events,
    read_curated_events,
)
from localguide.official_event_hub import event_finder_body, official_event_links
from scripts.event_candidates import add_candidates, approve_candidate, read_queue
from scripts.event_lifecycle import lifecycle

ROOT = Path(__file__).resolve().parents[1]


class CuratedEventPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "data/curated_events.json").write_text(
            json.dumps({"schema_version": 1, "editorial_policy": "human_review_pr_only",
                        "items": []}, ensure_ascii=False), encoding="utf-8")
        self.now = now_jst()
        self.source = "https://kakogawa-note.com/example-alert.html"
        self.fields = {
            "id": "test-review-one",
            "title": "架空のテスト用イベント",
            "municipality": "加古川市",
            "venue": "架空のテスト会場",
            "official_url": "https://www.city.kakogawa.lg.jp/example-for-tests.html",
            "start_on": (self.now + timedelta(days=1)).date().isoformat(),
            "end_on": (self.now + timedelta(days=9)).date().isoformat(),
            "checked_at": self.now.isoformat(),
            "review_note": "公式詳細を人が確認したものと仮定するテスト用データ",
        }

    def _save(self, events):
        (self.root / "data/curated_events.json").write_text(
            json.dumps({"schema_version": 1, "editorial_policy": "human_review_pr_only",
                        "items": events}, ensure_ascii=False), encoding="utf-8")

    def _stage(self):
        self.assertEqual(add_candidates(self.root, [self.source]), 1)
        self.assertEqual(add_candidates(self.root, [self.source]), 0)
        queued = read_queue(self.root)["items"]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]["state"], "needs_primary_confirmation")
        return queued[0]["id"]

    def test_candidates_are_private_and_unapproved_not_publishable(self):
        with patch("socket.create_connection", side_effect=AssertionError("network")):
            self._stage()
            self.assertEqual(read_curated_events(self.root, self.now), [])
            self.assertEqual(public_curated_events(self.root, self.now), [])
            self.assertFalse((self.root / "data/curated_events.json").read_text(encoding="utf-8").find(
                "kakogawa-note.com") >= 0)
            self.assertTrue((self.root / "cache/event_candidates.json").is_file())

    def test_approval_requires_explicit_human_review(self):
        cid = self._stage()
        fields = dict(self.fields, candidate_id=cid)
        with self.assertRaises(GuideError):
            approve_candidate(self.root, fields, owner_reviewed=False)
        self.assertEqual(read_curated_events(self.root, self.now), [])
        approved_id = approve_candidate(self.root, fields, owner_reviewed=True)
        self.assertEqual(approved_id, "test-review-one")
        self.assertEqual(read_queue(self.root)["items"][0]["state"], "approved")
        active = public_curated_events(self.root, self.now)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["information_scope"], "facts_only_owner_reviewed")
        self.assertNotIn("kakogawa-note.com", str(active))
        markup = event_finder_body(*official_event_links(ROOT), curated_event_cards(active))
        self.assertIn("架空のテスト用イベント", markup)
        self.assertIn("会場：架空のテスト会場", markup)
        self.assertIn("料金・年齢・定員・予約・変更・中止は主催者の公式案内で確認", markup)
        self.assertNotIn("<script", markup)
        self.assertNotIn(self.source, markup)

    def test_bad_urls_duplicate_events_and_future_checks_rejected(self):
        with self.assertRaises(GuideError):
            add_candidates(self.root, ["http://example.com/insecure"])
        with self.assertRaises(GuideError):
            add_candidates(self.root, ["https://example.com/?api_key=private"])
        event = dict(self.fields, review_state="approved", information_scope="facts_only_owner_reviewed")
        self._save([event])
        self.assertEqual(read_curated_events(self.root, self.now), [event])
        for bad in (
            dict(event, id="test-bad", title="<img src=evil>"),
            dict(event, id="test-bad", official_url="https://not-official.example/test"),
            dict(event, id="test-bad", start_on="9999-01-01", end_on="2026-01-01"),
            dict(event, id="test-bad", checked_at=(self.now + timedelta(days=1)).isoformat()),
            dict(event, id="test-bad", review_state="unreviewed"),
        ):
            with self.subTest(bad=bad):
                self._save([bad])
                with self.assertRaises(GuideError):
                    read_curated_events(self.root, self.now)
        self._save([event, dict(event, id="test-duplicate")])
        with self.assertRaises(GuideError):
            read_curated_events(self.root, self.now)

    def test_expiration_staleness_and_idempotent_lifecycle(self):
        event = dict(self.fields, review_state="approved", information_scope="facts_only_owner_reviewed")
        self._save([event])
        self.assertEqual(lifecycle(self.root, self.now, apply=False)["approved"], 1)
        self.assertEqual(lifecycle(self.root, self.now, apply=True)["changed"], 0)
        future = self.now + timedelta(hours=73)
        self.assertEqual(event_state(event, future), "needs_recheck")
        self.assertEqual(public_curated_events(self.root, future), [])
        status = lifecycle(self.root, future, apply=True)
        self.assertEqual(status["needs_recheck"], 1)
        self.assertEqual(status["changed"], 1)
        stored = read_json(self.root / "data/curated_events.json")["items"][0]
        self.assertEqual(stored["review_state"], "needs_recheck")
        self.assertEqual(stored["checked_at"], self.now.isoformat())
        self.assertEqual(lifecycle(self.root, future, apply=True)["changed"], 0)
        past_end = self.now + timedelta(days=11)
        status = lifecycle(self.root, past_end, apply=True)
        self.assertEqual(status["expired"], 1)
        self.assertEqual(status["changed"], 1)
        self.assertEqual(lifecycle(self.root, past_end, apply=True)["changed"], 0)

    def test_repo_has_no_curated_events_and_does_not_embed_external_scripts(self):
        self.assertEqual(public_curated_events(ROOT, now_jst()), [])
        body = event_finder_body(*official_event_links(ROOT))
        self.assertIn("個別イベントの掲載は現在準備中", body)
        self.assertIn("公式イベント案内", body)
        self.assertNotIn("<script", body)


if __name__ == "__main__":
    unittest.main()
