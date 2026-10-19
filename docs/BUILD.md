# Build from source / 从源码构建

Python 3.10+ is required. Original game data is **not** needed at build time.
First launch automatically downloads the fixed public firmware and validates all
prepared resources. `--public` stages only the host, CA roots, native sound
preparation helper, manifest and original black-and-white application icon.
Personal saves and original game data must not be included in release packages.

`native/audio.c` embeds the MIT TinySoundFont header. Build it for each target
before staging; `native/bin/` is ignored by Git. Release source and compiled
helpers are provided separately. The helper contains no Nokia samples.

## Linux

Install the distribution's GTK3/PyGObject/Cairo packages and Python dependencies.
Run `python tools/build_audio.py`, then `python app.py` from the repository.
`sound.py` uses libpulse's simple API. The Linux package includes both ARM64 and
x86_64 preparation helpers; the running architecture is selected automatically.

## Windows x64

On Windows, install Python, then run from this repository:

```powershell
py -m pip install -r requirements.txt
py tools/build_audio.py --compiler gcc
py tools/prepare.py desktop --public
py build/app/windows_app.py
```

Use a matching MinGW GCC compiler for the Windows helper.
The source host uses ctypes, Win32/GDI and winsound, without a web view. Optional
portable packaging can embed a matching Python runtime, Unicorn and Pillow next
to the staged payload. `ports/windows_launcher.c` is the launcher source used
for that layout; it expects `_internal/pythonw.exe` and `_internal/app/`.

## macOS Apple Silicon

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pyobjc-framework-Cocoa pyinstaller
.venv/bin/python tools/build_audio.py
.venv/bin/python tools/prepare.py desktop --public
.venv/bin/python build/app/mac_app.py
```

Optional app bundle:

```sh
.venv/bin/pyinstaller --windowed --name 'Snake Xenzia' \
  --osx-bundle-identifier local.snake.xenzia \
  --paths build/app --add-data 'build/app/assets:assets' \
  --add-data 'build/app/certs:certs' --add-data 'build/app/native:native' \
  --add-data 'build/app/licenses:licenses' \
  --hidden-import startup_mac --collect-all unicorn build/app/mac_app.py
```

Sign/notarize separately for distribution; no developer signing credentials are
included. A local unsigned bundle may need the normal macOS user approval.

## Android ARM64

Requirements: JDK 21, Gradle 8.14.3, Android SDK platform 36, Python 3.12 on the
build host, and an Android ARM64 `libunicorn.so` built from Unicorn 2.1.4. Build
the latter using upstream's CMake build and the Android NDK toolchain, targeting
ARM, Android API 24 and `arm64-v8a`; a desktop library cannot be substituted.

For the published Android library (NDK 27.3):

```sh
cmake -S unicorn-2.1.4 -B unicorn-android \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" \
  -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-24 \
  -DUNICORN_ARCH=arm -DUNICORN_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-z,max-page-size=16384"
cmake --build unicorn-android --parallel
```

```sh
python -m pip install -r requirements.txt
python tools/build_audio.py --android-ndk "$ANDROID_NDK_HOME"
python tools/prepare.py android --public \
  --unicorn-library /path/to/android/arm64-v8a/libunicorn.so \
  --audio-library native/bin/libxenzia_audio.so
cd ports/android
gradle --no-daemon assembleDebug
```

Use `ANDROID_HOME` for the SDK and `PYTHON312` if Python 3.12 is not named
`python3.12`. A system Gradle installation is needed; the wrapper JAR is not
vendored. For a signed release, set `NOKIA_KEYSTORE` and `NOKIA_STORE_PASSWORD`,
with key alias `snake-xenzia`, then use `assembleRelease`. Do not commit a
keystore or its password. Minimum Android version is 7.0; only ARM64 is configured.

## Validation

`python test_auto_assets.py` checks verified download/cache behaviour, certificate
verification, corrupt input rejection, archive parsing and save isolation.
`test_asset_import.py` covers optional offline migration. Core/game tests require
prepared resources; see the README and release validation report.

## 中文

构建时不需要原版资源。先构建目标平台的音效准备动态库，再用 `tools/prepare.py ... --public`
生成不含原版游戏数据的发布目录。首次启动会自动获取并校验资源，不再弹出 ZIP 导入器。

Linux 执行 `python tools/build_audio.py`、`python app.py`。Windows 使用匹配架构的
MinGW GCC 编译 helper；macOS 使用 Clang，打包时包含 `certs/`、`native/` 和 `startup_mac`。
安卓需要 JDK 21、Gradle、SDK 36、Python 3.12、Android ARM64 Unicorn 2.1.4，以及通过 NDK
构建的 `libxenzia_audio.so`。两种动态库都应支持 16 KB 页，不能拿桌面库替代。

音效 helper 不包含 Nokia 采样；其源码和 MIT TinySoundFont 头文件均在仓库中。
不要把个人存档、原版数据、签名密钥或密码加入公开包。运行与安装所用资源保存在用户数据目录，
与应用更新分离。
