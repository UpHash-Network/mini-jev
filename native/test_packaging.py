"""Small local transport fixtures; no download, compilation, or model execution."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetcher = load('mini_fetch_test', BASE / 'fetch_native_model.py')
packager = load('mini_package_test', BASE / 'native/package_runtime.py')
DATA = b'GGUF-small-test-fixture'
PIN = {**fetcher.PIN, 'bytes': len(DATA), 'sha256': hashlib.sha256(DATA).hexdigest()}


class Response(io.BytesIO):
    def __init__(self, data, status=200, **headers):
        super().__init__(data)
        self.status = status
        self.headers = headers


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / 'test.gguf'
        self.partial = self.output.with_name('test.gguf.partial')

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self, response, **kwargs):
        return fetcher.fetch(self.output, pin=PIN, opener=lambda *a, **k: response, **kwargs)

    def test_pinned_metadata(self):
        self.assertTrue(all(fetcher.metadata()[k] == v for k, v in fetcher.PIN.items()))

    def test_verified_download_publishes_and_records_receipt(self):
        result = self.fetch(Response(DATA))
        self.assertTrue(result['verified'])
        self.assertEqual(self.output.read_bytes(), DATA)
        self.assertFalse(self.partial.exists())
        self.assertTrue(self.output.with_name('test.gguf.verified.json').is_file())
        self.assertFalse(self.output.with_name('test.gguf.download.lock').exists())

    def test_resume_requires_exact_content_range(self):
        self.partial.write_bytes(DATA[:5])
        def opener(request, **kwargs):
            self.assertEqual(request.get_header('Range'), 'bytes=5-')
            return Response(DATA[5:], status=206, **{'Content-Range': f'bytes 5-{len(DATA)-1}/{len(DATA)}'})
        fetcher.fetch(self.output, pin=PIN, opener=opener)
        self.assertEqual(self.output.read_bytes(), DATA)

    def test_server_ignoring_range_restarts_partial(self):
        self.partial.write_bytes(b'old-data')
        self.fetch(Response(DATA))
        self.assertEqual(self.output.read_bytes(), DATA)

    def test_incomplete_does_not_publish_and_retains_partial(self):
        with self.assertRaises(ValueError):
            self.fetch(Response(DATA[:4]))
        self.assertFalse(self.output.exists())
        self.assertEqual(self.partial.read_bytes(), DATA[:4])

    def test_wrong_hash_never_publishes(self):
        with self.assertRaises(ValueError):
            self.fetch(Response(b'x' * len(DATA)))
        self.assertFalse(self.output.exists())
        self.assertTrue(self.partial.exists())

    def test_existing_invalid_file_is_preserved(self):
        self.output.write_bytes(b'user-data')
        with self.assertRaises(ValueError):
            self.fetch(Response(DATA))
        self.assertEqual(self.output.read_bytes(), b'user-data')

    def test_verify_only_never_uses_network(self):
        self.output.write_bytes(DATA)
        def forbidden(*args, **kwargs):
            self.fail('network access during verify-only')
        fetcher.fetch(self.output, pin=PIN, verify_only=True, opener=forbidden)

    def test_full_partial_verifies_without_download(self):
        self.partial.write_bytes(DATA)
        def forbidden(*args, **kwargs):
            self.fail('unnecessary download')
        fetcher.fetch(self.output, pin=PIN, opener=forbidden)
        self.assertEqual(self.output.read_bytes(), DATA)

    def test_bad_range_length_and_oversize_fail_closed(self):
        for response in [Response(DATA, status=206, **{'Content-Range':'bytes 1-9/10'}),
                         Response(DATA, **{'Content-Length':'2'}), Response(DATA+b'x')]:
            with self.subTest(response=response), self.assertRaises(ValueError):
                self.fetch(response)
            self.assertFalse(self.output.exists())

    def test_existing_lock_and_symlinks_rejected(self):
        lock = self.output.with_name('test.gguf.download.lock')
        lock.write_text('someone else')
        with self.assertRaises(ValueError):
            self.fetch(Response(DATA))
        self.assertEqual(lock.read_text(), 'someone else')
        lock.unlink()
        self.output.symlink_to(self.output.with_name('elsewhere'))
        with self.assertRaises(ValueError):
            self.fetch(Response(DATA))


class PackageTests(unittest.TestCase):
    def test_source_licenses_exist(self):
        source = BASE.parent.parent / 'work/llama-cpp'
        if not source.exists():
            self.skipTest('source checkout not present')
        for name in packager.LICENSES:
            self.assertTrue((source/name).is_file(), name)

    def test_hash_inventory_detects_tampering_and_bad_links(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'bin').mkdir()
            (root/'bin/helper').write_bytes(b'fixture')
            (root/'bin/link').symlink_to('helper')
            packager.write_manifest(root, provenance={'test_fixture':True})
            self.assertTrue(packager.verify_package(root)['verified'])
            (root/'bin/helper').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                packager.verify_package(root)
            (root/'bin/link').unlink()
            (root/'bin/link').symlink_to('/etc/hosts')
            with self.assertRaises(ValueError):
                packager.inventory(root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
