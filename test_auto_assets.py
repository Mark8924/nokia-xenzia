"""First-run integrity, cache and save-isolation checks; no original data bundled."""
import contextlib
import hashlib
import io
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest import mock
import zlib
import auto_assets as setup
import asset_store


def record(name, payload, method=0x30):
    name = name.encode('ascii')
    header = bytearray(32 + len(name))
    struct.pack_into('<HBHH', header, 0, 0, 0x74, 0, len(header))
    struct.pack_into('<II', header, 7, len(payload), len(payload))
    struct.pack_into('<I', header, 16, zlib.crc32(payload))
    header[24] = 29; header[25] = method
    struct.pack_into('<H', header, 26, len(name))
    header[32:] = name
    return bytes(header) + payload


class FirstRun(unittest.TestCase):
    def test_stored_archive_whitelist_and_crc(self):
        archive = b'Rar!\x1a\x07\x00' + record('pm.pm', b'unused', 0x35)
        archive += record('rh93_07.02ej', b'ppm fixture')
        archive += record('rh930_nai7.02ej', b'nai fixture')
        self.assertEqual(setup.stored_rar_files(archive), {'rh93_07.02ej': b'ppm fixture', 'rh930_nai7.02ej': b'nai fixture'})
        with self.assertRaises(ValueError): setup.stored_rar_files(archive[:-1] + b'X')
        unsafe = b'Rar!\x1a\x07\x00' + record('../rh93_07.02ej', b'escape')
        with self.assertRaises(ValueError): setup.stored_rar_files(unsafe)

    def test_verified_download_cache_and_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.bin'
            payload = b'fixture content'
            expected = hashlib.sha256(payload).hexdigest()
            with mock.patch.object(setup.urllib.request, 'urlopen', return_value=io.BytesIO(payload)) as fetch:
                self.assertEqual(setup.download('https://example.test/source', path, expected, len(payload), lambda _: None), payload)
                self.assertEqual(fetch.call_count, 1)
                context = fetch.call_args.kwargs['context']
                self.assertTrue(context.check_hostname)
                self.assertEqual(context.verify_mode, setup.ssl.CERT_REQUIRED)
            with mock.patch.object(setup.urllib.request, 'urlopen', side_effect=AssertionError('network must not be used')):
                self.assertEqual(setup.download('https://example.test/source', path, expected, len(payload), lambda _: None), payload)
            path.unlink()
            with mock.patch.object(setup.time, 'sleep'), mock.patch.object(setup.urllib.request, 'urlopen', side_effect=lambda *_args, **_kwargs: io.BytesIO(b'corrupt')):
                with self.assertRaises(RuntimeError): setup.download('https://example.test/source', path, expected, len(payload), lambda _: None)
            self.assertFalse(path.exists(), 'unverified input must never become a cached source')

    def test_failed_preparation_preserves_saves_and_previous_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); host = root / 'host'; data = root / 'data'
            (host / 'assets').mkdir(parents=True); data.mkdir()
            for name in ('manifest.json', 'icon.png'): shutil.copyfile(setup.ROOT / 'assets' / name, host / 'assets' / name)
            (data / 'save.state').write_bytes(b'user progress fixture')
            (data / 'settings.json').write_text('{"muted":true}')
            (data / 'assets').mkdir(); (data / 'assets/marker').write_bytes(b'previous assets')
            before = {p.name: p.read_bytes() for p in data.iterdir() if p.is_file()}
            with mock.patch.object(setup, 'ROOT', host), mock.patch.object(asset_store, 'ROOT', host):
                with self.assertRaises(ValueError): setup.obtain(data, firmware=b'bad firmware')
            self.assertEqual(before, {p.name: p.read_bytes() for p in data.iterdir() if p.is_file()})
            self.assertEqual((data / 'assets/marker').read_bytes(), b'previous assets')

    def test_unsupported_flash_is_rejected(self):
        for value in (b'', b'bad', b'\0\0\0\0\0\x14\x01'):
            with self.assertRaises(ValueError): setup.flash_records(value)


if __name__ == '__main__':
    unittest.main()
