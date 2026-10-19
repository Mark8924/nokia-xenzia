# Build from source / 从源码构建

Import the supported assets first, as described in the README. Python 3.10+ is
required. Build products and imported assets are ignored by Git. Do not publish
packages containing original resources without the necessary rights.

For a distributable host without Nokia resources, add `--public` to either
`tools/prepare.py desktop` or `tools/prepare.py android ...`. This stages only
the compatibility code, resource manifest and generated host icon. On first
launch the compiled application offers a local resource import dialog. Imported
data lives beside the user's saves, separate from the installed application.
`test_asset_import.py` covers ZIP validation and saved-speed compatibility.

## Linux

Install the distribution's GTK3/PyGObject/Cairo packages and Python dependencies.
Run `python app.py` from the repository. `sound.py` uses libpulse's simple API.

## Windows x64

On Windows, install Python, then run from this repository:

```powershell
py -m pip install -r requirements.txt
py tools/prepare.py desktop
py build/app/windows_app.py
```

The source host uses ctypes, Win32/GDI and winsound, without a web view. Optional
portable packaging can embed a matching Python runtime, Unicorn and Pillow next
to the staged payload. `ports/windows_launcher.c` is the launcher source used
for that layout; it expects `_internal/pythonw.exe` and `_internal/app/`.

## macOS Apple Silicon

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pyobjc-framework-Cocoa pyinstaller
.venv/bin/python tools/prepare.py desktop
.venv/bin/python build/app/mac_app.py
```

Optional app bundle:

```sh
.venv/bin/pyinstaller --windowed --name 'Snake Xenzia' \
  --osx-bundle-identifier local.snake.xenzia \
  --paths build/app --add-data 'build/app/assets:assets' \
  --collect-all unicorn build/app/mac_app.py
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
  -DUNICORN_ARCH=arm -DUNICORN_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=ON
cmake --build unicorn-android --parallel
```

```sh
python -m pip install -r requirements.txt
python tools/prepare.py android --unicorn-library /path/to/android/arm64-v8a/libunicorn.so
cd ports/android
gradle --no-daemon assembleDebug
```

Use `ANDROID_HOME` for the SDK and `PYTHON312` if Python 3.12 is not named
`python3.12`. A system Gradle installation is needed; the wrapper JAR is not
vendored. For a signed release, set `NOKIA_KEYSTORE` and `NOKIA_STORE_PASSWORD`,
with key alias `snake-xenzia`, then use `assembleRelease`. Do not commit a
keystore or its password. Minimum Android version is 7.0; only ARM64 is configured.

## 中文

先按 README 导入原版资源。Linux 可直接运行 `app.py`；Windows 和 macOS 先执行
`tools/prepare.py desktop`，再运行 `build/app/` 下对应的原生界面。准备工具会生成
播放用 WAV 和 Windows ICO，不会读取个人存档。

安卓需要 JDK 21、Gradle 8.14.3、SDK 36、Python 3.12，以及面向 Android ARM64
交叉编译的 Unicorn 2.1.4 动态库。桌面版动态库无法用于安卓。仓库不含个人签名密钥、
密码、SDK 安装路径或预编译的原版资源包。
