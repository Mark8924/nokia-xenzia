"""Stage a desktop or Android host, with optional local resources."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import wave
import zipfile
from import_assets import validated_files

ROOT = Path(__file__).resolve().parents[1]


def payload(public=False, target=None):
    files = [] if public else validated_files(ROOT / 'assets', json.loads((ROOT / 'assets/manifest.json').read_text()))
    target = target or ROOT / 'build/app'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('runtime.py', 'asset_store.py', 'auto_assets.py', 'audio_layout.py', 'dct4_format.py', 'startup_mac.py', 'startup_windows.py', 'controls.py', 'qa_play.py', 'test_frame_budget.py', 'test_transitions.py'):
        shutil.copyfile(ROOT / name, target / name)
    for name in ('session.py', 'test_portable.py', 'windows_app.py', 'mac_app.py'):
        shutil.copyfile(ROOT / 'ports' / name, target / name)
    (target / 'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'assets/manifest.json', target / 'assets/manifest.json')
    shutil.copytree(ROOT / 'certs', target / 'certs', dirs_exist_ok=True)
    shutil.copytree(ROOT / 'native/bin', target / 'native', dirs_exist_ok=True)
    (target / 'licenses').mkdir()
    for source in (ROOT / 'LICENSE', ROOT / 'third_party/nokia-recomp-LICENSE', ROOT / 'audio-source/LICENSE-TinySoundFont'):
        shutil.copyfile(source, target / 'licenses' / source.name)
    for source, relative in files:
        out = target / 'assets' / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out)
    for pcm in (target / 'assets/audio').glob('effect-*.s16le'):
        with wave.open(str(pcm.with_suffix('.wav')), 'wb') as output:
            output.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
            output.writeframes(pcm.read_bytes())
    from PIL import Image
    if public:
        shutil.copyfile(ROOT / 'assets/icon.png', target / 'assets/icon.png')
    Image.open(target / 'assets/icon.png').convert('RGBA').resize((256, 256), Image.Resampling.NEAREST).save(
        target / 'assets/icon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return target


def android(target, library, audio_library=None):
    if not library or not library.is_file():
        raise ValueError('--unicorn-library must name an Android arm64 libunicorn.so built from Unicorn 2.1.4')
    app = ROOT / 'ports/android/app/src/main'
    (app / 'assets').mkdir(parents=True, exist_ok=True)
    archive = app / 'assets/game.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for file in sorted(target.rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts and 'native' not in file.relative_to(target).parts:
                output.write(file, file.relative_to(target))
    (app / 'assets/game.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
    (app / 'jniLibs/arm64-v8a').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(library, app / 'jniLibs/arm64-v8a/libunicorn.so')
    if audio_library is None or not audio_library.is_file():
        raise ValueError('--audio-library must name the Android ARM64 first-run audio helper')
    shutil.copyfile(audio_library, app / 'jniLibs/arm64-v8a/libxenzia_audio.so')
    import unicorn
    bindings = Path(unicorn.__file__).parent
    out = app / 'python/unicorn'
    shutil.copytree(bindings, out, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('lib', '__pycache__', '*.pyc', '*.so', '*.dylib', '*.dll'))
    loader = out / 'unicorn_py3/unicorn.py'
    code = loader.read_text()
    old = "canonicals = resources.files('unicorn') / 'lib'"
    if old not in code:
        raise ValueError('Unicorn loader differs from supported 2.1.4; inspect before packaging')
    loader.write_text(code.replace(old, "canonicals = Path(os.environ['LIBUNICORN_PATH'])"))
    from PIL import Image
    for name, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        folder = app / ('res/mipmap-' + name)
        folder.mkdir(parents=True, exist_ok=True)
        Image.open(target / 'assets/icon.png').resize((size, size), Image.Resampling.LANCZOS).save(folder / 'ic_launcher.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=['desktop', 'android'])
    parser.add_argument('--unicorn-library', type=Path)
    parser.add_argument('--audio-library', type=Path)
    parser.add_argument('--public', action='store_true', help='Build the host without game resources; prepare them automatically on first launch')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        target = payload(args.public, args.output)
        if args.platform == 'android':
            android(target, args.unicorn_library, args.audio_library)
        print('Prepared:', target)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
