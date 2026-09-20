"""Negative fixtures for the release gate; no model or network needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'check_public_release.py'
SPEC = importlib.util.spec_from_file_location('check_public_release', MODULE)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class PublicReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def scan(self):
        return CHECKER.scan_tree(self.root, require_project=False)

    def test_clean_text_passes(self):
        (self.root / 'readme.md').write_text('User-supplied JSONL and reproducible evaluation.')
        self.assertTrue(self.scan()['passed'])

    def test_credential_does_not_appear_in_report(self):
        token = 'ghp_' + 'x' * 36
        (self.root / 'bad.txt').write_text(token)
        report = self.scan()
        self.assertFalse(report['passed'])
        self.assertNotIn(token, json.dumps(report))
        self.assertEqual(report['findings'][0]['code'], 'credential_pattern')

    def test_private_path_in_binary_is_rejected_without_echo(self):
        private = '/' + '/'.join(['Users', 'example-user', 'private', 'file.cpp'])
        (self.root / 'library.bin').write_bytes(b'\0binary\0' + private.encode())
        report = self.scan()
        self.assertFalse(report['passed'])
        self.assertNotIn(private, json.dumps(report))
        self.assertTrue(report['findings'][0]['binary'])

    def test_external_work_path_rejected(self):
        path = '../' * 2 + 'work/python'
        (self.root / 'run.sh').write_text('exec ' + path)
        self.assertEqual(self.scan()['findings'][0]['code'], 'external_development_workspace')

    def test_broken_symlink_rejected(self):
        (self.root / 'broken').symlink_to('missing')
        self.assertEqual(self.scan()['findings'][0]['code'], 'unsafe_symlink')

    def test_external_symlink_rejected(self):
        (self.root / 'external').symlink_to(self.root.parent)
        self.assertEqual(self.scan()['findings'][0]['code'], 'unsafe_symlink')

    def test_local_symlink_allowed(self):
        (self.root / 'target').write_text('content')
        (self.root / 'alias').symlink_to('target')
        self.assertTrue(self.scan()['passed'])

    def test_ignored_virtual_environment_is_not_scanned(self):
        folder = self.root / '.venv'
        folder.mkdir()
        (folder / 'temporary').write_text('ghp_' + 'x' * 36)
        self.assertTrue(self.scan()['passed'])

    def test_environment_example_allowed_but_live_env_blocked(self):
        (self.root / '.env.example').write_text('PORT=8765')
        self.assertTrue(self.scan()['passed'])
        (self.root / '.env').write_text('PORT=8765')
        self.assertFalse(self.scan()['passed'])

    def test_model_file_is_not_source(self):
        (self.root / 'model.gguf').write_bytes(b'GGUF')
        self.assertEqual(self.scan()['findings'][0]['code'], 'model_weights_in_source_release')

    def test_missing_project_requirements_fail(self):
        report = CHECKER.scan_tree(self.root)
        self.assertFalse(report['passed'])
        self.assertIn('missing_release_file', {item['code'] for item in report['findings']})


if __name__ == '__main__':
    unittest.main()
