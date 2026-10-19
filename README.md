# Nokia Snake Xenzia — original-program compatibility layer

[English](#english) · [中文](#中文)

## English

Run the original **Snake Xenzia ARM/Thumb program** from Nokia 1110i / 1112
RH-93 firmware 7.02 (2007-12-10) on current computers and Android devices.
The game logic is not rewritten: its original code controls the snake, food,
collisions, scoring, speed, mazes, campaign progression and animations.

**This public repository contains the host source, not Nokia's game binaries
or media assets.** Supply the supported extracted assets before running or
building. This is an independent project, not an official Nokia release.

### Features

- Original Classic, Modern and Campaign modes, speed levels 1–9 and six mazes.
- Native interfaces: GTK on Linux, Win32 on Windows, Cocoa on macOS and Java on Android.
- Keyboard, touch/swipe and optional on-screen direction buttons.
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

Python 3.10 or newer is required. On Arch, install the host dependencies:

```sh
sudo pacman -S python-gobject gtk3 python-cairo python-pillow python-unicorn libpulse
```

Provide a supported extracted `assets/` directory, then import it:

```sh
python tools/import_assets.py /path/to/your/extracted/assets
python app.py
```

The importer validates the full SHA-256 manifest before copying. It only imports
the listed original resources; it never copies saves, settings or unrelated files.
`assets/manifest.json` lists the exact supported extraction. A raw phone firmware
image is **not** an asset directory; this tool does not decrypt firmware or fetch
game data. See [provenance](docs/PROVENANCE.md) for the research tools and formats.

For Windows, macOS and Android source builds, see [BUILD.md](docs/BUILD.md).
The public [release](https://github.com/Mark8924/nokia-xenzia/releases/latest)
is a source-only compatibility-layer preview, without original resources.

### Controls

| Action | Controls |
| --- | --- |
| Direction | Arrow keys, WASD, 2 / 4 / 6 / 8, touch buttons or display swipe |
| Select / pause | Enter / 5; on-screen Select |
| Back / pause | Esc / P; on-screen Back |
| Fullscreen on desktop | F11 |

Touch direction buttons act on contact. Fast consecutive valid turns are queued
in order. The original game still turns at its own grid boundaries; a slower
native speed setting therefore waits longer before a turn takes effect.

### Tests

After importing assets, run the isolated core tests:

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
Native builds were locally exercised on Arch ARM64, Android ARM64, macOS Apple
Silicon and a Windows x64 compatibility environment. They are not a claim that
every device, firmware version or game state has been tested.

### License

New compatibility-layer and host code: [MIT](LICENSE).
Third-party libraries keep their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
Nokia's original program, fonts, text, icon and sound samples are not relicensed
by this project and are supplied separately.

## 中文

这是在现代电脑和安卓设备上运行 **Nokia 原版 Snake Xenzia 程序**的兼容层。
对应 Nokia 1110i / 1112 的 RH-93 7.02 固件（2007-12-10）。蛇的运动、食物、
碰撞、计分、速度、迷宫、闯关与动画由原版 ARM/Thumb 程序执行，不是重写玩法的复刻。

**公开仓库只包含兼容层与各平台界面源码，不包含 Nokia 原版程序和资源。**
运行和构建前需自行提供对应的提取资源。项目与 Nokia 官方无关联。

功能包括原版 Classic / Modern / Campaign 模式、1–9 级速度、六种迷宫、
键盘与触屏操作、可隐藏的方向按钮、正反色、可选启动动画、自动暂停及本地存档。
音效使用原程序的音符、乐器和时长参数，以及从原固件提取的音色采样。

Linux 使用 GTK，Windows 使用 Win32，macOS 使用 Cocoa，Android 使用原生 Java 界面。
没有账号、联网服务、遥测或开机常驻。

### Arch 运行

```sh
sudo pacman -S python-gobject gtk3 python-cairo python-pillow python-unicorn libpulse
python tools/import_assets.py /你的/已提取资源/assets
python app.py
```

导入工具先校验完整 SHA-256 清单，只复制清单中的资源；不会导入存档、个人设置或其他文件。
原始固件不能直接交给这个导入工具，它不负责固件解密或自动下载。
资源格式和研究工具见 [PROVENANCE.md](docs/PROVENANCE.md)，其他平台构建见
[BUILD.md](docs/BUILD.md)。公开 Release 是不含原版资源的兼容层源码预览包。

方向键、WASD、2468 和屏幕按钮控制方向；Enter / 5 选择或暂停，Esc / P 返回，
桌面版 F11 全屏。快速连续转弯会依次排队，但转向仍按原版游戏的格点节奏发生。

这里执行的是原版二进制，**没有恢复原游戏的 C/C++ 源码，也没有模拟整台手机**。
手机系统菜单由兼容层按原字符串、回调与字体重建；音效不宣称完全复现原机 DSP 和喇叭。
测试覆盖食物、长蛇、存档和闯关过场等场景，不代表所有设备或所有状态都没有问题。

新编写代码采用 MIT 许可，第三方组件和 Nokia 资源的权利分别保留。
