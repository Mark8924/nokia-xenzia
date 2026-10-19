"""Import integrity, atomic failure, allowlist and saved-speed regressions."""
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile
from asset_store import ROOT, manifest, import_assets, ensure_assets, resource


def main():
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        archive = directory / 'original.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for name in manifest():
                output.write(ROOT / 'assets' / name, 'package/assets/' + name)
            output.writestr('../settings.json', 'do not import')
            output.writestr('package/save.state', 'do not import')
        data = directory / 'data'
        import_assets(archive, data)
        assert not (data / 'settings.json').exists()
        assert not (data / 'save.state').exists()
        assert resource('audio/effect-0.wav').read_bytes().startswith(b'RIFF')
        original_hash = hashlib.sha256(resource('snake-code.bin').read_bytes()).digest()
        bad = directory / 'bad.zip'
        with zipfile.ZipFile(bad, 'w') as output:
            output.writestr('snake-code.bin', b'damaged')
        try:
            import_assets(bad, data)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid import accepted')
        assert hashlib.sha256(resource('snake-code.bin').read_bytes()).digest() == original_hash
        from runtime import NokiaRuntime
        fresh = NokiaRuntime()
        assert fresh.word(fresh.state + 4) == 4
        while not fresh.menu:
            fresh.frame()
        fresh.activate(fresh.menu_labels().index('Level'))
        assert fresh.overlay['value'] == 3
        fresh.overlay['value'] = 6
        fresh.key('select')
        save = data / 'save.state'
        fresh.save(save)
        restored = NokiaRuntime()
        restored.restore(save)
        assert restored.word(restored.state + 4) == 7
    os.environ.pop('SNAKE_XENZIA_ASSETS', None)
    print('PASS: ZIP import, allowlist, atomic invalid-import rejection, PCM conversion, default 4, saved speed 7')


if __name__ == '__main__':
    main()
