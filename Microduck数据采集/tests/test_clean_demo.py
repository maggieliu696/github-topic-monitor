"""Offline regression tests for release timestamps across collection and export."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zlib

BASE = Path(__file__).resolve().parents[1]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

collector = load('collector_release_tests', 'collector.py')
cleaner = load('clean_demo_release_tests', 'clean_demo.py')

CREATED = '2026-09-01T01:02:03Z'
PUBLISHED = '2026-09-03T04:05:06Z'
UPDATED = '2026-09-05T07:08:09Z'
RELEASE_URL = 'https://github.com/a/b/releases/tag/v1.0.0'
API_URL = 'https://api.github.com/repos/a/b/releases?per_page=100'


class ReleaseTimestampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / 'research.sqlite3'
        self.store = collector.Store(self.db_path)
        catalog = self.root / '.cognitive-research/microduck-user-research/developers100/coded-projects.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text('[]')

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def api_release(self, **dates):
        return dict(id=42, name='Release 1', tag_name='v1.0.0', html_url=RELEASE_URL,
                    body='A meaningful release note.', author={'login': 'author'}, **dates)

    def collect(self, release):
        client = collector.Client(self.store, self.root, {'github': 10})

        def get(platform, url, optional=False):
            if url.endswith('/readme'):
                return None, {}
            return {'id': 1, 'full_name': 'a/b', 'html_url': 'https://github.com/a/b',
                    'owner': {'login': 'a'}}, {}

        client.get = get
        client.pages = lambda platform, url, *args, **kwargs: iter(
            [[release]] if '/releases?' in url else [[]])
        config = {'github': {'repos': ['a/b'], 'queries': [], 'repo_limit': 1, 'max_pages': 1}}
        run = collector.Collector(self.store, client, config, 'test-run')
        run.github()
        self.assertEqual(run.coverage['github']['completed_repositories'], 1)
        return json.loads(self.store.rows(
            'SELECT payload FROM items WHERE id=?', ('github:release:42',))[0][0])

    def put_normalized_release(self, updated=None, **meta):
        record = collector.item('github', 'release:42', 'release', 'Release 1',
                                RELEASE_URL, 'A meaningful release note.', 'author',
                                updated=updated, repo='a/b', **meta)
        self.store.put('test-run', record)

    def cache_release(self, original):
        self.store.db.execute('INSERT INTO cache VALUES(?,?,?,?,?)',
                              (API_URL, None, None,
                               zlib.compress(json.dumps([original]).encode()), '{}'))
        self.store.db.commit()

    def export_release(self):
        output = self.root / 'export'
        with mock.patch.object(cleaner, 'ROOT', self.root / 'app'):
            cleaner.clean(self.db_path, output)
        rows = [json.loads(line) for line in (output / '清洗后信息.jsonl').read_text().splitlines()]
        return next(row for row in rows if row['record_id'] == 'github:release:42')

    def test_collector_preserves_distinct_release_dates(self):
        record = self.collect(self.api_release(created_at=CREATED,
                                               published_at=PUBLISHED, updated_at=UPDATED))
        self.assertEqual(record['meta']['created_at'], CREATED)
        self.assertEqual(record['meta']['published_at'], PUBLISHED)
        self.assertEqual(record['source_updated_at'], UPDATED)
        exported = self.export_release()
        self.assertEqual(exported['published_at'], PUBLISHED)
        self.assertEqual(exported['updated_at'], UPDATED)

    def test_collector_missing_release_dates_remain_unknown(self):
        record = self.collect(self.api_release(created_at=CREATED))
        self.assertEqual(record['meta']['created_at'], CREATED)
        self.assertIn('published_at', record['meta'])
        self.assertIsNone(record['meta']['published_at'])
        self.assertIsNone(record['source_updated_at'])
        exported = self.export_release()
        self.assertIsNone(exported['published_at'])
        self.assertIsNone(exported['updated_at'])
        self.assertTrue(exported['first_captured_at'])

    def test_cleaner_repairs_legacy_mapping_from_same_database_raw_cache(self):
        # Previous collector versions put publication in the update field.
        self.put_normalized_release(updated=PUBLISHED)
        self.cache_release(self.api_release(created_at=CREATED,
                                            published_at=PUBLISHED, updated_at=UPDATED))
        exported = self.export_release()
        self.assertEqual(exported['published_at'], PUBLISHED)
        self.assertEqual(exported['updated_at'], UPDATED)
        self.assertNotEqual(exported['published_at'], CREATED)
        self.assertNotEqual(exported['published_at'], exported['first_captured_at'])

    def test_raw_missing_dates_do_not_fall_back_to_stale_metadata_or_creation(self):
        self.put_normalized_release(updated=UPDATED, created_at=CREATED,
                                    published_at=PUBLISHED)
        self.cache_release(self.api_release(created_at=CREATED))
        exported = self.export_release()
        self.assertIsNone(exported['published_at'])
        self.assertIsNone(exported['updated_at'])

    def test_raw_null_dates_remain_unknown(self):
        self.put_normalized_release(updated=UPDATED, created_at=CREATED,
                                    published_at=PUBLISHED)
        self.cache_release(self.api_release(created_at=CREATED,
                                            published_at=None, updated_at=None))
        exported = self.export_release()
        self.assertIsNone(exported['published_at'])
        self.assertIsNone(exported['updated_at'])

    def test_without_raw_cache_legacy_update_field_is_not_trusted(self):
        self.put_normalized_release(updated=PUBLISHED, created_at=CREATED)
        exported = self.export_release()
        self.assertIsNone(exported['published_at'])
        self.assertIsNone(exported['updated_at'])

    def test_raw_release_match_uses_id_not_list_position(self):
        self.put_normalized_release(updated=PUBLISHED)
        unrelated = self.api_release(created_at=CREATED,
                                      published_at='2001-01-01T00:00:00Z', updated_at=None)
        unrelated['id'] = 99
        actual = self.api_release(created_at=CREATED,
                                  published_at=PUBLISHED, updated_at=UPDATED)
        self.store.db.execute('INSERT INTO cache VALUES(?,?,?,?,?)',
                              (API_URL, None, None,
                               zlib.compress(json.dumps([unrelated, actual]).encode()), '{}'))
        self.store.db.commit()
        exported = self.export_release()
        self.assertEqual(exported['published_at'], PUBLISHED)
        self.assertEqual(exported['updated_at'], UPDATED)


if __name__ == '__main__':
    unittest.main()
