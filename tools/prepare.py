"""Stage a local desktop or Android payload after importing original assets."""
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
    for name in ('runtime.py', 'asset_store.py', 'controls.py', 'qa_play.py', 'test_frame_budget.py', 'test_transitions.py'):
        shutil.copyfile(ROOT / name, target / name)
    for name in ('session.py', 'test_portable.py', 'windows_app.py', 'mac_app.py'):
        shutil.copyfile(ROOT / 'ports' / name, target / name)
    (target / 'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'assets/manifest.json', target / 'assets/manifest.json')
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
        from PIL import ImageDraw
        icon=Image.new('RGBA',(256,256),(223,231,205,255));draw=ImageDraw.Draw(icon)
        draw.rounded_rectangle((12,12,244,244),radius=40,fill=(39,49,37,255))
        draw.line([(65,171),(65,93),(111,93),(111,143),(166,143),(166,78)],fill=(224,237,189,255),width=23,joint='curve')
        draw.rectangle((160,64,184,88),fill=(224,237,189,255));draw.rectangle((177,67,181,71),fill=(39,49,37,255))
        icon.save(target/'assets/icon.png')
    Image.open(target / 'assets/icon.png').convert('RGBA').resize((256, 256), Image.Resampling.NEAREST).save(
        target / 'assets/icon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return target


def android(target, library):
    if not library or not library.is_file():
        raise ValueError('--unicorn-library must name an Android arm64 libunicorn.so built from Unicorn 2.1.4')
    app = ROOT / 'ports/android/app/src/main'
    (app / 'assets').mkdir(parents=True, exist_ok=True)
    archive = app / 'assets/game.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for file in sorted(target.rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts:
                output.write(file, file.relative_to(target))
    (app / 'assets/game.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
    (app / 'jniLibs/arm64-v8a').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(library, app / 'jniLibs/arm64-v8a/libunicorn.so')
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
    parser.add_argument('--public', action='store_true', help='Build the host without proprietary resources; enable first-run import')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        target = payload(args.public, args.output)
        if args.platform == 'android':
            android(target, args.unicorn_library)
        print('Prepared:', target)
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')
