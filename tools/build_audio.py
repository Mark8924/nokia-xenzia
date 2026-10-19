"""Build the small first-run renderer; no game samples are compiled into it."""
import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', default=os.environ.get('CC', 'cc'))
parser.add_argument('--android-ndk', type=Path)
args = parser.parse_args()
machine = {'arm64': 'aarch64', 'amd64': 'x86_64'}.get(platform.machine().lower(), platform.machine().lower())
folder = ROOT / 'native/bin'; folder.mkdir(exist_ok=True)
if args.android_ndk:
    host = 'darwin-x86_64' if sys.platform == 'darwin' else 'linux-x86_64'
    compiler = str(args.android_ndk / 'toolchains/llvm/prebuilt' / host / 'bin/aarch64-linux-android24-clang')
    name = 'libxenzia_audio.so'
    flags = ['-fPIC', '-shared', '-Wl,-z,max-page-size=16384', '-lm']
elif sys.platform == 'darwin':
    compiler, name, flags = args.compiler, 'macos-' + machine + '.dylib', ['-dynamiclib']
elif sys.platform == 'win32':
    compiler, name, flags = args.compiler, 'windows-' + machine + '.dll', ['-shared', '-lm']
else:
    compiler, name, flags = args.compiler, 'linux-' + machine + '.so', ['-fPIC', '-shared', '-lm']
command = [compiler, '-O2', str(ROOT / 'native/audio.c'), '-o', str(folder / name), *flags]
subprocess.run(command, check=True)
print('Built:', folder / name)
