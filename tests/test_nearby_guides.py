"""No-network coverage of manually curated outing cards and static publication."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from localguide.core import GuideError, parse_time
from localguide.nearby_guides import HOME_FEATURES, NEARBY_IMAGES, IMAGE_NOTICE, nearby_cards, nearby_image, nearby_page_body, nearby_preview_cards, reviewed_nearby
from localguide.site import Document, PHOTO_ASSETS, create_files, load_photo_asset, validate_site

ROOT = Path(__file__).resolve().parents[1]
NOW = parse_time("2026-10-19T18:00:00+09:00")


class NearbyGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "data/nearby_spots.json").read_text(encoding="utf-8"))

    def _validate(self, data):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "data"
            target.mkdir()
            (target / "nearby_spots.json").write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return reviewed_nearby(Path(temporary))

    def test_reviewed_official_only_unique_curated_candidates(self):
        records = reviewed_nearby(ROOT)
        self.assertGreaterEqual(len(records), 9)
        self.assertEqual(len({record["id"] for record in records}), len(records))
        self.assertTrue({'gongen-park', 'mitoro-hill', 'kakurinji-park', 'shikata-east-park'} <= {record['id'] for record in records})
        self.assertTrue(all(record["official_url"].startswith("https://") for record in records))
        self.assertEqual({record["municipality"] for record in records},
                         {"加古川市", "明石市", "播磨町"})
        self.assertEqual(len(self._validate(self.record)), len(records))

    def test_missing_data_is_empty_for_synthetic_workspaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(reviewed_nearby(temporary), [])

    def test_malicious_markup_unapproved_host_and_duplicate_id_stop(self):
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][0]["idea"] = '<script>alert("x")</script>'
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][1]["official_url"] = "https://tracking.example.net/fake"
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["items"][1]["id"] = unsafe["items"][0]["id"]
        with self.assertRaises(GuideError):
            self._validate(unsafe)
        unsafe = copy.deepcopy(self.record)
        unsafe["editorial_policy"] = "auto_scrape_all"
        with self.assertRaises(GuideError):
            self._validate(unsafe)

    def test_cards_are_accessible_and_dont_invent_prices_or_visits(self):
        cards = nearby_cards(reviewed_nearby(ROOT))
        self.assertEqual(cards.count('class="card nearby-card"'), len(self.record['items']))
        self.assertEqual(cards.count('rel="noopener noreferrer"'), len(self.record['items']))
        self.assertNotIn("<script", cards)
        self.assertIn("料金・営業時間・年齢条件：施設ごとに公式案内で確認", cards)
        self.assertIn("大中遺跡公園", cards)
        self.assertIn("権現総合公園", cards)
        self.assertIn("みとろの丘", cards)
        self.assertIn("加古川海洋文化センター", cards)
        self.assertIn("公式リンクの最終編集確認日", nearby_page_body(
            reviewed_nearby(ROOT), self.record["reviewed_on"]))

    def test_generated_site_shows_new_guide_without_indexing_or_ad_changes(self):
        files, _ = create_files(ROOT, NOW)
        self.assertIn("nearby.html", files)
        nearby_page = files["nearby.html"]
        home = files["index.html"]
        self.assertIn('content="noindex,follow"', nearby_page)
        self.assertIn('<h1>近場のよりみちガイド</h1>', nearby_page)
        self.assertEqual(nearby_page.count("<h1"), 1)
        self.assertIn('href="nearby.html"', home)
        self.assertIn('id="nearby-guide"', home)
        self.assertIn(f'{len(self.record["items"])}件の候補を見る', home)
        self.assertIn('href="nearby.html" aria-current="page"', nearby_page)
        self.assertLess(home.index('id="family-trip"'), home.index('id="nearby-guide"'))
        self.assertLess(home.index('id="nearby-guide"'), home.index('id="local-spots"'))
        self.assertNotIn("sitemap.xml", files)
        self.assertEqual(files[".guide-manifest.json"].count('"events": 0'), 1)

    def test_six_preview_links_resolve_to_reviewed_guidance(self):
        items = reviewed_nearby(ROOT)
        previews = nearby_preview_cards(items)
        details = nearby_cards(items)
        self.assertEqual(previews.count('class="card nearby-preview-card"'), 6)
        self.assertEqual(previews.count('<img '), 6)
        self.assertEqual(previews.count(IMAGE_NOTICE), 6)
        for spot_id in HOME_FEATURES:
            self.assertIn(f'href="nearby.html#{spot_id}"', previews)
            self.assertIn(f'id="{spot_id}"', details)
        malicious = copy.deepcopy(items)
        malicious[0]["name"] = '<img src=x onerror=alert(1)>'
        self.assertNotIn('<img src=x', nearby_preview_cards(malicious))

    def test_local_photos_validate_and_missing_image_fails_site_validation(self):
        files, _ = create_files(ROOT, NOW)
        home = files['index.html']
        self.assertEqual(home.count('loading="lazy" decoding="async"'), 6)
        self.assertIn('画像に描かれた風景・設備の実在を保証するものではありません', home)
        self.assertEqual(files['nearby.html'].count('<img '), 10)
        self.assertEqual(files['nearby.html'].count(IMAGE_NOTICE), 10)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for name, content in files.items():
                if isinstance(content, bytes):
                    (output / name).write_bytes(content)
                else:
                    (output / name).write_text(content, encoding='utf-8')
            validate_site(output)
            missing = NEARBY_IMAGES['gongen-park'][0]
            (output / missing).unlink()
            manifest = json.loads((output / '.guide-manifest.json').read_text(encoding='utf-8'))
            manifest['files'].remove(missing)
            (output / '.guide-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaises(GuideError):
                validate_site(output)

    def test_external_or_modified_image_markup_is_rejected(self):
        markup = nearby_preview_cards(reviewed_nearby(ROOT))
        first_image = markup[markup.index('<img'):markup.index('>', markup.index('<img')) + 1]
        # A valid local image is accepted inside a figure.
        document = Document()
        document.feed('<figure>' + first_image + '</figure>')
        self.assertFalse(document.errors)
        for unsafe in (first_image.replace('src="nearby-gongen-park.webp"',
                                         'src="https://unreviewed.example/photo.webp"'),
                       first_image.replace('src="nearby-gongen-park.webp"', 'src="../nearby-gongen-park.webp"'),
                       first_image.replace('width="960"', 'width="1"'),
                       first_image.replace('alt="', 'alt="unreviewed '),
                       first_image.replace('loading="lazy"', 'onerror="alert(1)"')):
            document = Document()
            document.feed('<figure>' + unsafe + '</figure>')
            self.assertTrue(document.errors)

    def test_asset_loader_rejects_unlisted_missing_and_invalid_webp(self):
        with self.assertRaises(GuideError):
            load_photo_asset('unreviewed.webp')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch('localguide.site.PHOTO_ASSET_ROOT', root):
                with self.assertRaises(GuideError):
                    load_photo_asset('nearby-hero.webp')
                (root / 'nearby-hero.webp').write_bytes(b'not an image')
                with self.assertRaises(GuideError):
                    load_photo_asset('nearby-hero.webp')

    def test_owner_manifest_matches_all_ten_registered_original_webps(self):
        manifest = json.loads((ROOT / 'localguide/assets/nearby_image_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(set(NEARBY_IMAGES), {'hero'} | {item['id'] for item in self.record['items']})
        self.assertEqual(len(manifest['images']), 10)
        for image in manifest['images']:
            spec = NEARBY_IMAGES[image['id']]
            self.assertEqual(spec, (image['filename'], image['alt'], image['width'], image['height']))
            self.assertIn(image['filename'], PHOTO_ASSETS)
            data = load_photo_asset(image['filename'])
            self.assertEqual(hashlib.sha256(data).hexdigest(), image['sha256'])
            self.assertEqual(len(data), image['bytes'])
        hero = nearby_image('hero', hero=True)
        self.assertIn('loading="eager" fetchpriority="high"', hero)
        self.assertNotIn('loading="lazy"', hero)


if __name__ == "__main__":
    unittest.main()
