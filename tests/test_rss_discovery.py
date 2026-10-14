"""No-network RSS discovery tests. XML inputs contain fake articles only."""
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from localguide.core import GuideError, atomic_json, parse_time, read_json
from localguide.rss_discovery import extract_candidates, reviewed_for_discovery, stage_snapshot

NOW = parse_time("2026-10-14T19:00:00+09:00")
URL = "https://example.org/feed/"
RSS = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>Fixture</title>
<item><title>Test Halloween event</title><link>https://example.org/post/0</link><pubDate>Tue, 13 Oct 2026 11:00:00 +0900</pubDate></item>
</channel></rss>"""
# Use synthetic Japanese labels only in the test.
EVENT = '<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><item><title>架空マルシェの開催</title><link>https://example.org/post/1</link><pubDate>Tue, 13 Oct 2026 11:00:00 +0900</pubDate><description>DO NOT SAVE TEXT</description></item><item><title>架空カフェ開店</title><link>https://example.org/post/2</link></item><item><title>普通の記事</title><link>https://example.org/post/3</link></item></channel></rss>'.encode()


def fixture_source():
    return {
        "id": "demo_rss", "kind": "general_news_rss", "url": URL,
        "rss_discovery_review_status": "allowed",
        "rss_discovery_checked_at": NOW.isoformat(),
        "rss_discovery_permission_document": "https://example.org/permission",
        "terms_review_status": "allowed",
        "robots_review_status": "allowed",
        "enabled": False
    }


class RSSParsingTests(unittest.TestCase):
    def test_rss2_extracts_no_copyrighted_text(self):
        results = extract_candidates(EVENT, "demo_rss", URL, NOW)
        self.assertEqual(len(results), 2)
        self.assertEqual({r["candidate_kind"] for r in results}, {"possibly_event", "possibly_store_news"})
        self.assertNotIn("title", results[0])
        self.assertNotIn("description", results[0])
        self.assertNotIn("event_start_at", results[0])
        self.assertFalse(all(x["publishable"] for x in results))
        self.assertTrue(all(x["review_state"] == "needs_primary_confirmation" for x in results))

    def test_rss_article_date_not_event_date(self):
        result = extract_candidates(EVENT, "demo_rss", URL, NOW)[0]
        self.assertEqual(result["article_published_at"], "2026-10-13")
        self.assertNotIn("event_date", result)

    def test_atom_link_with_href(self):
        atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>架空イベント</title><link href="https://example.org/post/atom" rel="alternate"/><updated>2026-10-14T07:00:00+09:00</updated></entry></feed>'.encode()
        self.assertEqual(len(extract_candidates(atom, "demo_rss", URL, NOW)), 1)

    def test_rdf_rss1_date(self):
        rdf = '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>架空マルシェ</title><link>https://example.org/post/rdf</link><dc:date>2026-10-14</dc:date></item></rdf:RDF>'.encode()
        record = extract_candidates(rdf, "demo_rss", URL, NOW)[0]
        self.assertEqual(record["article_published_at"], "2026-10-14")

    def test_offdomain_and_unrelated_ignored(self):
        body = EVENT.replace(b"https://example.org/post/1", b"https://evil.example.org/post/1")
        self.assertEqual(len(extract_candidates(body, "demo_rss", URL, NOW)), 1)

    def test_reject_dtd_and_entity(self):
        with self.assertRaises(GuideError):
            extract_candidates(b'<!DOCTYPE foo [<!ENTITY x "a">]><rss/>', "demo_rss", URL, NOW)

    def test_reject_html(self):
        with self.assertRaises(GuideError):
            extract_candidates(b'<html><title>demo</title></html>', "demo_rss", URL, NOW)

    def test_reject_size_limit(self):
        with self.assertRaises(GuideError):
            extract_candidates(b"x" * (1024 * 1024 + 1), "demo_rss", URL, NOW)

    def test_hash_stable(self):
        a = extract_candidates(EVENT, "demo_rss", URL, NOW)
        b = extract_candidates(EVENT, "demo_rss", URL, NOW + timedelta(days=1))
        self.assertEqual([x["candidate_id"] for x in a], [x["candidate_id"] for x in b])


class RSSStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "config").mkdir()
        self.xml = self.root / "example.xml"
        self.xml.write_bytes(EVENT)
        self.source = fixture_source()
        self.save()

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        atomic_json(self.root / "config/sources.json", {"schema_version": 1, "sources": [self.source]})

    def test_without_approval_no_queue_created(self):
        self.source["rss_discovery_review_status"] = "unverified"
        self.save()
        with self.assertRaises(GuideError):
            stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        self.assertFalse((self.root / "cache/rss_discovery_queue.json").exists())

    def test_expired_permission_rejected(self):
        self.source["rss_discovery_checked_at"] = (NOW - timedelta(days=31)).isoformat()
        self.save()
        with self.assertRaises(GuideError):
            stage_snapshot(self.root, "demo_rss", self.xml, NOW)

    def test_unverified_terms_rejected(self):
        self.source["terms_review_status"] = "unverified"
        self.save()
        with self.assertRaises(GuideError):
            stage_snapshot(self.root, "demo_rss", self.xml, NOW)

    def test_source_can_stay_disabled_for_public_while_offline_staging(self):
        self.assertFalse(self.source["enabled"])
        state = stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        self.assertEqual(state, {"discovered": 2, "queued": 2})
        queue = read_json(self.root / "cache/rss_discovery_queue.json")
        self.assertEqual(len(queue["items"]), 2)
        self.assertFalse(any(x["publishable"] for x in queue["items"]))
        self.assertEqual(queue["schema_version"], 1)
        self.assertFalse((self.root / "data/events.json").exists())
        self.assertFalse((self.root / "docs").exists())

    def test_reimport_deduplicates(self):
        stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        again = stage_snapshot(self.root, "demo_rss", self.xml, NOW + timedelta(days=1))
        self.assertEqual(again["queued"], 2)
        rows = read_json(self.root / "cache/rss_discovery_queue.json")["items"]
        self.assertEqual({x["discovered_at"] for x in rows}, {NOW.isoformat()})
        self.assertEqual({x["last_seen_at"] for x in rows}, {(NOW + timedelta(days=1)).isoformat()})

    def test_corrupted_queue_cannot_be_promoted_to_public(self):
        stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        target = self.root / "cache/rss_discovery_queue.json"
        state = read_json(target)
        state["items"][0]["publishable"] = True
        state["items"][0]["review_state"] = "approved"
        atomic_json(target, state)
        with self.assertRaises(GuideError):
            stage_snapshot(self.root, "demo_rss", self.xml, NOW)

    def test_unknown_source_rejected(self):
        with self.assertRaises(GuideError):
            stage_snapshot(self.root, "wrong", self.xml, NOW)

    def test_no_new_items_keeps_prior_candidates(self):
        stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        self.xml.write_bytes(b"<rss><channel><title>Nothing</title></channel></rss>")
        again = stage_snapshot(self.root, "demo_rss", self.xml, NOW)
        self.assertEqual(again, {"discovered": 0, "queued": 2})


if __name__ == "__main__":
    unittest.main()
