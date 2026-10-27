import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('scope_collector',Path(__file__).resolve().parents[1]/'collector.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class ScopeTests(unittest.TestCase):
    def test_only_github_can_be_requested(self):
        self.assertEqual(c.active_platforms('github'), ['github'])
        for value in ['huggingface','hackernews','github,huggingface','','github,github']:
            with self.assertRaises(ValueError):c.active_platforms(value)
