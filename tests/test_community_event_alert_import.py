"""Public community links remain distinct; EML/RSS imports stay offline/private."""
from email.message import EmailMessage
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from localguide.community_event_sources import (
    community_event_section, reviewed_community_event_sources,
)
from localguide.core import GuideError, now_jst
from localguide.site import create_files
from scripts.event_candidates import read_queue
from scripts.import_alert_urls import (
    extract_candidate_urls, import_alert_urls, normalize_candidate_url,
)

ROOT = Path(__file__).resolve().parents[1]


class CommunityEventLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(
            (ROOT / "data/community_event_sources.json").read_text(encoding="utf-8")
        )

    def _validate(self, doc):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "data").mkdir()
            (root / "data/community_event_sources.json").write_text(
                json.dumps(doc, ensure_ascii=False), encoding="utf-8"
            )
            return reviewed_community_event_sources(root)

    def test_two_explicit_text_links_and_policies(self):
        entries, date = self._validate(self.original)
        self.assertEqual(len(entries), 2)
        self.assertEqual(date, "2026-10-27")
        urls = {v["url"] for v in entries}
        self.assertEqual(urls, {
            "https://kakogawa-note.com/category/event/",
            "https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/",
        })
        fragment = community_event_section(entries, date)
        self.assertEqual(fragment.count('class="card community-event-source-card"'), 2)
        self.assertIn("地域の民間イベント情報サイト", fragment)
        self.assertIn("自治体等の公式イベント案内とは区別", fragment)
        self.assertIn("各サイトの公認・提携を示すものではありません", fragment)
        self.assertNotIn("<script", fragment)
        self.assertNotIn("<img", fragment)
        self.assertNotIn("<iframe", fragment)
        self.assertNotIn("target=", fragment)

    def test_malicious_and_changed_domain_policy_duplicate_fail_closed(self):
        edits = [
            lambda doc: doc["items"][0].update({"url": "https://unreviewed.example/events"}),
            lambda doc: doc["items"][0].update({"url": "https://kakogawa-note.com.attacker.example/category/event/"}),
            lambda doc: doc["items"][1].update({"url": "https://abc-housing.asahi.co.jp/kinki/park/kakogawa.html"}),
            lambda doc: doc["items"][1].update({"link_policy_url": "https://other.example/"}),
            lambda doc: doc["items"][0].update({"description": "<script>alert(1)</script>"}),
            lambda doc: doc["items"][1].update({"id": "kakogawa-note"}),
            lambda doc: doc.update({"policy": "auto_scrape_all_posts"}),
            lambda doc: doc["items"].append(dict(doc["items"][0])),
        ]
        for edit in edits:
            doc = copy.deepcopy(self.original)
            edit(doc)
            with self.subTest(doc=doc):
                with self.assertRaises(GuideError):
                    self._validate(doc)

    def test_site_page_has_separated_links_and_index_remains_safe(self):
        files, _ = create_files(ROOT, now_jst())
        event_html = files["official-events.html"]
        self.assertIn("<h1>地域のイベント情報を探す</h1>", event_html)
        self.assertEqual(event_html.count('class="card event-source-card"'), 11)
        self.assertEqual(event_html.count('class="card community-event-source-card"'), 2)
        self.assertIn("地域の民間イベント情報サイト", event_html)
        self.assertIn('content="noindex,follow"', event_html)
        self.assertNotIn('src="https://kakogawa-note.com', event_html)
        self.assertNotIn('src="https://abc-housing.asahi.co.jp', event_html)
        self.assertNotIn("Googleアラート", event_html)
        self.assertIn('href="official-events.html"', files["index.html"])


class OfflineAlertImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "cache/inbox").mkdir(parents=True)

    def _file(self, basename, content):
        p = self.root / "cache/inbox" / basename
        p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        return p

    def test_normalizes_google_redirect_and_marketing_query(self):
        url = (
            "https://www.google.com/url?sa=t&url="
            "https%3A%2F%2Fkakogawa-note.com%2Fcategory%2Fevent%2F"
            "%3Futm_source%3Dgoogle%26a%3D1"
        )
        self.assertEqual(normalize_candidate_url(url),
                         "https://kakogawa-note.com/category/event/?a=1")
        self.assertEqual(normalize_candidate_url("https://kakogawa-note.com/test#fragment"),
                         "https://kakogawa-note.com/test")
        self.assertIsNone(normalize_candidate_url("https://www.google.com/alerts/feeds/1/2"))
        self.assertIsNone(normalize_candidate_url("https://suspicious.example/events"))
        self.assertIsNone(normalize_candidate_url("http://kakogawa-note.com/category/event/"))
        self.assertIsNone(normalize_candidate_url("https://abc-housing.asahi.co.jp:444/events"))

    def test_eml_extracts_urls_only_not_text_or_tracking(self):
        msg = EmailMessage()
        msg["From"] = "Google Alerts <googlealerts-noreply@google.com>"
        msg["To"] = "recipient@example.com"
        msg["Subject"] = "加古川 イベント"
        msg.set_content("sample copy with email address and private content")
        msg.add_alternative(
            '<p>有料記事内容（転載禁止）</p>'
            '<a href="https://kakogawa-note.com/category/event/?utm_medium=email">'
            '個別の記事説明</a>'
            '<a href="https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/">'
            '住宅展示場</a>'
            '<a href="https://kakogawa-note.com/category/event/?utm_source=other">duplicate</a>'
            '<a href="https://www.google.com/alerts/feedback">track</a>'
            '<a href="https://suspicious.example/posts">off-topic</a>'
            '<img src="https://kakogawa-note.com/image.jpg">',
            subtype="html"
        )
        p = self._file("alert.eml", msg.as_bytes())
        with patch("socket.create_connection", side_effect=AssertionError("offline")):
            urls = extract_candidate_urls(p, self.root)
            self.assertEqual(urls, [
                "https://kakogawa-note.com/category/event/",
                "https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/",
            ])
            self.assertEqual(import_alert_urls(self.root, [p], dry_run=True), (2, 0))
            self.assertFalse((self.root / "cache/event_candidates.json").exists())
            self.assertEqual(import_alert_urls(self.root, [p]), (2, 2))
            self.assertEqual(import_alert_urls(self.root, [p]), (2, 0))
        doc = read_queue(self.root)
        self.assertEqual(len(doc["items"]), 2)
        self.assertTrue(all(entry["state"] == "needs_primary_confirmation" for entry in doc["items"]))
        serialized = (self.root / "cache/event_candidates.json").read_text(encoding="utf-8")
        self.assertNotIn("有料記事内容", serialized)
        self.assertNotIn("recipient@example.com", serialized)
        self.assertNotIn("image.jpg", serialized)
        self.assertNotIn("utm_source", serialized)

    def test_rss_and_atom_only_item_links(self):
        rss = self._file("one.rss", (
            "<rss><channel><link>https://kakogawa-note.com/ignore-header</link>"
            "<item><title>転載しない記事</title><link>"
            "https://kakogawa-note.com/category/event/"
            "</link><description>転載禁止</description></item>"
            "</channel></rss>"
        ))
        atom = self._file("two.xml", (
            '<feed xmlns="http://www.w3.org/2005/Atom">'
            '<entry><title>本文を掲載しない</title>'
            '<link rel="alternate" href="https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/" />'
            '<link rel="self" href="https://www.google.com/alerts/feeds/1/2" />'
            '</entry></feed>'
        ))
        urls = extract_candidate_urls(rss, self.root)
        self.assertEqual(urls, ["https://kakogawa-note.com/category/event/"])
        self.assertEqual(extract_candidate_urls(atom, self.root), [
            "https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/",
        ])
        self.assertEqual(import_alert_urls(self.root, [rss, atom]), (2, 2))

    def test_invalid_xml_and_out_of_cache_files_rejected_without_writing(self):
        evil = self._file("bad.xml", '<!DOCTYPE x [<!ENTITY z "hi">]><rss/>')
        with self.assertRaises(GuideError):
            import_alert_urls(self.root, [evil])
        external = self.root / "personal-private.eml"
        external.write_text("secret email", encoding="utf-8")
        with self.assertRaises(GuideError):
            import_alert_urls(self.root, [external])
        good = self._file("good.rss", (
            "<rss><channel><item><link>https://kakogawa-note.com/category/event/</link>"
            "</item></channel></rss>"
        ))
        with self.assertRaises(GuideError):
            import_alert_urls(self.root, [good, evil])
        self.assertFalse((self.root / "cache/event_candidates.json").exists())

    def test_only_candidate_urls_survive_two_inputs_no_external_requests(self):
        a = self._file("a.rss", (
            "<rss><channel><item><link>https://www.city.kakogawa.lg.jp/abc</link>"
            "</item></channel></rss>"
        ))
        b = self._file("b.rss", (
            "<rss><channel><item><link>https://www.city.kakogawa.lg.jp/abc</link>"
            "</item></channel></rss>"
        ))
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            self.assertEqual(import_alert_urls(self.root, [a, b]), (1, 1))
        self.assertEqual(read_queue(self.root)["items"][0]["url"],
                         "https://www.city.kakogawa.lg.jp/abc")


if __name__ == "__main__":
    unittest.main()
