# Nokia Snake Xenzia — original-program compatibility layer

[English](#english) · [中文](#中文)

## English

Run the original **Snake Xenzia ARM/Thumb program** from Nokia 1110i / 1112
RH-93 firmware 7.02 (2007-12-10) on current computers and Android devices.
The game logic is not rewritten: its original code controls the snake, food,
collisions, scoring, speed, mazes, campaign progression and animations.

### Download — no compilation needed

| Platform | Ready-built download |
| --- | --- |
| Arch Linux / Arch Linux ARM | [Installable package](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/nokia-xenzia-host-1.1.0-1-any.pkg.tar.xz) |
| Android 7+ · ARM64 | [Install APK](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-Android-arm64.apk) |
| Windows 10/11 · x64 | [Portable ZIP](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-Windows-x64.zip) |
| macOS · Apple Silicon | [Application ZIP](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-macOS-AppleSilicon.zip) |

[Release notes and all files](https://github.com/Mark8924/nokia-xenzia/releases/latest)

**Install, open, and play.** On the first launch the application automatically
fetches the supported public firmware (3.7 MB), extracts the original program,
fonts and samples, renders the effects, and checks every resource against the
SHA-256 manifest. A native window shows progress and offers retry if preparation
fails. No ZIP import, external extraction tool, compiler or extra download is
needed. Subsequent launches work offline.

Public packages contain the compatibility host and preparation tools; original
Nokia game data is obtained on the user's device. The program, fonts, strings and
five rendered PCM effects are checked byte-for-byte against the working reference.
A failed verification never starts the game or replaces existing resources.
[Source details and hashes](docs/PROVENANCE.md).
No Python installation is needed on Android, Windows or macOS; Arch installs
its dependencies through pacman. Default speed is **4**; saved choices, high
scores and progress are preserved.

Windows: extract the entire ZIP before opening `SnakeXenzia.exe`.
macOS: move `Snake Xenzia.app` into Applications. The preview is locally signed,
not Apple-notarized. Windows 11 ARM can use the x64 compatibility layer; a native
Windows ARM64 build is not included.

### Features

- Original Classic, Modern and Campaign modes, speed levels 1–9 and six mazes.
- Native interfaces: GTK on Linux, Win32 on Windows, Cocoa on macOS and Java on Android.
- Keyboard, touch/swipe and optional four-button direction pad; its centre stays empty to avoid accidental pauses.
- Original colours, black-on-white and white-on-black display options.
- Optional original opening animation, enabled separately from saved progress.
- Automatic pause and local saves; no account, telemetry, server or autostart service.
- Sampled effects triggered by the original game's note/instrument/duration commands.
- Ordered turn buffering and regression coverage for food, long snakes and campaign wipes.

### What is original, and what is the host?

Unicorn 2.1.4 executes the supported unmodified big-endian ARMv4T program.
`runtime.py` implements the Nokia NAI APIs it calls and renders a 96×65 pixel
framebuffer. The phone operating system's menu widgets are reconstructed using
the game's strings, callbacks and extracted bitmap fonts. This is application
compatibility, **not full-phone emulation** and not recovered C/C++ game source.

Sound effects use samples extracted from the firmware's DLS bank and rendered
offline with TinySoundFont. The original phone DSP, filters and physical speaker
are not emulated exactly.

### Start on Arch Linux

Download the package above, then install it and launch from the application list:

```sh
sudo pacman -U ./nokia-xenzia-host-1.1.0-1-any.pkg.tar.xz
snake-xenzia
```

Pacman resolves the dependencies. First launch automatically prepares the game
with a graphical progress window. The architecture-independent Python/GTK host uses Arch's native Unicorn
package, including on ARM64. Other Linux distributions can run from source.

For a source checkout, Python 3.10 or newer is required. On Arch:

```sh
sudo pacman -S python-gobject gtk3 python-cairo python-pillow python-unicorn libpulse
```

Build the small sound-preparation helper, then launch:

```sh
python tools/build_audio.py
python app.py
```

The same automatic first-run preparation runs from source. For Windows, macOS
and Android source builds, see [BUILD.md](docs/BUILD.md). The optional local
`tools/import_assets.py` remains available for offline migration of previously
verified extracted resources; normal users do not need it.

### Controls

| Action | Controls |
| --- | --- |
| Direction | Arrow keys, WASD, 2 / 4 / 6 / 8, touch buttons or display swipe |
| Select / pause | Enter / 5; on-screen Select |
| Back / pause | Esc / P; on-screen Back |
| Fullscreen on desktop | F11 |

The on-screen direction pad contains only 2 / 4 / 6 / 8. Its centre has no button or click target; use the separate Select / Pause control instead. The physical 5 key still works.

Touch direction buttons act on contact. Fast consecutive valid turns are queued
in order. The original game still turns at its own grid boundaries; a slower
native speed setting therefore waits longer before a turn takes effect.

### Tests

[Automatic setup validation — 1.1.0](docs/AUTO-SETUP-VALIDATION.md) · [Arch game regression](docs/ARCH-VALIDATION.md)

After automatic preparation, run the isolated core tests:

```sh
python test_runtime.py
python test_compatibility.py
python test_sound_controls.py
python test_frame_budget.py
python test_transitions.py
python qa_play.py
python qa_food_maze.py
python qa_campaign.py
```

`qa_startup.py` additionally needs GTK and a graphical session. These tests create
isolated instances and temporary output, without modifying installed progress.
See the release validation report for the exact build and test environments.
Tests do not imply that every device or game state has been tested.

### License

New compatibility-layer and host code: [MIT](LICENSE).
Third-party libraries keep their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
The application uses the original black-and-white icon from the initial local
version; it remains the property of its respective rights holders and is not
covered by MIT. Nokia's original program, fonts, text and sound samples are not
relicensed by this project and are supplied separately.

## 中文

### 安装后打开即可玩

- [Arch / Arch Linux ARM 安装包](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/nokia-xenzia-host-1.1.0-1-any.pkg.tar.xz)
- [Android ARM64 安装包](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-Android-arm64.apk)
- [Windows x64 便携版](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-Windows-x64.zip)
- [macOS Apple Silicon 应用](https://github.com/Mark8924/nokia-xenzia/releases/download/v1.1.0-preview/SnakeXenzia-1.1.0-preview-macOS-AppleSilicon.zip)
- [版本说明与全部下载](https://github.com/Mark8924/nokia-xenzia/releases/latest)

首次打开会自动获取支持的公开固件（约 3.7 MB），提取原版程序、字体、文字与音色，
生成音效并逐项校验；界面显示进度，网络失败可以重试。**不需要自己找 ZIP、导入、解压或编译。**
准备完成后可以离线玩。公开安装包提供兼容层与自动准备工具，原版游戏数据在用户设备上获取。
程序、字体、文字以及五种播放用 PCM 音效均与参考版本逐字节校验，不一致就报错，不使用近似替代品。

Windows 请完整解压后打开 `SnakeXenzia.exe`；Windows ARM64 可通过系统 x64 兼容层运行。
Mac 将 `Snake Xenzia.app` 放进应用程序；当前预览版为本地签名，未经 Apple 公证。
安卓安装 APK 即可，最低 Android 7、仅 ARM64。Arch 安装方式：

```sh
sudo pacman -U ./nokia-xenzia-host-1.1.0-1-any.pkg.tar.xz
snake-xenzia
```

默认速度 **4**，保留已有存档、高分与设置。屏幕方向按钮只有 2 / 4 / 6 / 8，中间留空；
使用单独的选择／暂停键，实体 5 键仍保留。支持实体键盘、触屏按钮、滑动操作、方向键显隐、
正反色、可选开场动画、自动暂停与本地存档。

蛇的运动、食物、碰撞、计分、速度、迷宫、闯关和过场动画由 **Nokia 1110i / 1112
RH-93 7.02 的原版 ARM/Thumb 二进制程序**执行。这里没有恢复原游戏的 C/C++ 源码，也没有
模拟整台手机；手机系统菜单由兼容层按原字符串、回调和字体重建。音效使用原版命令和采样，
不宣称完全模拟原机的 DSP、滤波和物理喇叭。

方向键、WASD、2468 控制方向；Enter / 5 选择或暂停，Esc / P 返回，桌面 F11 全屏。
快速连续转弯会依次排队，但转向仍按原版格点节奏发生。没有账号、遥测或开机常驻服务。

从源码运行：安装依赖后执行 `python tools/build_audio.py`、`python app.py`，同样会自动准备。
详细构建见 [BUILD.md](docs/BUILD.md)，数据来源与校验见 [PROVENANCE.md](docs/PROVENANCE.md)。
新编写代码采用 MIT 许可；第三方组件、最初黑白图标和 Nokia 原版资源的权利分别保留，
详见 [THIRD-PARTY.md](THIRD-PARTY.md)。本项目与 Nokia 官方无关联。
