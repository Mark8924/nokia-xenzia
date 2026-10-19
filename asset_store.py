"""Hash-checked local resource import for compiled compatibility hosts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import wave
import zipfile

ROOT = Path(__file__).resolve().parent
MAX_FILE = 16 * 1024 * 1024


def matches_hash(content, expected):
    return hashlib.sha256(content).hexdigest() in (expected if isinstance(expected, list) else [expected])


def resource(name):
    return Path(os.environ.get('SNAKE_XENZIA_ASSETS', ROOT / 'assets')) / name


def manifest():
    return json.loads((ROOT / 'assets/manifest.json').read_text())


def complete(directory):
    try:
        for name, digest in manifest().items():
            path = Path(directory) / name
            if not path.is_file() or path.stat().st_size > MAX_FILE:
                return False
            if not matches_hash(path.read_bytes(), digest):
                return False
        return True
    except (OSError, ValueError):
        return False


def ensure_assets(data):
    for directory in (ROOT / 'assets', Path(data) / 'assets'):
        if complete(directory):
            os.environ['SNAKE_XENZIA_ASSETS'] = str(directory)
            return True
    return False


def import_assets(source, data):
    """Validate all resources before import; never execute input or copy saves."""
    source, data = Path(source), Path(data)
    expected = manifest()
    data.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='asset-import-', dir=data) as temporary:
        stage = Path(temporary) / 'assets'
        stage.mkdir()

        def store(name, content):
            if len(content) > MAX_FILE or not matches_hash(content, expected[name]):
                raise ValueError('Unsupported or damaged resource: ' + name)
            out = stage / name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(content)

        if source.is_dir():
            for name in expected:
                path = source / name
                if not path.resolve().is_relative_to(source.resolve()):
                    raise ValueError('Resource escapes selected directory')
                if path.stat().st_size > MAX_FILE:
                    raise ValueError('Resource is too large: ' + name)
                store(name, path.read_bytes())
        else:
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                for name, digest in expected.items():
                    suffix = tuple(Path(name).parts)
                    candidates = [entry for entry in entries if not entry.is_dir() and
                                  tuple(Path(entry.filename).parts[-len(suffix):]) == suffix]
                    found = False
                    for entry in candidates:
                        if entry.file_size > MAX_FILE:
                            continue
                        with archive.open(entry) as stream:
                            content = stream.read(MAX_FILE + 1)
                        if matches_hash(content, digest):
                            store(name, content)
                            found = True
                            break
                    if not found:
                        raise ValueError('Missing or unsupported resource: ' + name)
        for pcm in (stage / 'audio').glob('effect-*.s16le'):
            with wave.open(str(pcm.with_suffix('.wav')), 'wb') as output:
                output.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                output.writeframes(pcm.read_bytes())
        target, previous = data / 'assets', data / 'assets.previous'
        if previous.exists():
            shutil.rmtree(previous)
        if target.exists():
            target.rename(previous)
        try:
            stage.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise
        if previous.exists():
            shutil.rmtree(previous)
    os.environ['SNAKE_XENZIA_ASSETS'] = str(target)
    return True
