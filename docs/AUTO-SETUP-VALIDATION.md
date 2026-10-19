# Automatic preparation validation — 1.1.0 Preview

## English

Empty user directories were used for first-launch tests. The public hosts
contained only the icon and manifest in `assets/`; no installed game data was
borrowed. Downloads used the fixed HTTPS firmware source and SHA-256 check.

- macOS Apple Silicon: native progress window → automatic download/extraction →
  game menu → gameplay/save/intro/long-snake/campaign regression tests passed.
- Windows x64 under CrossOver: the same first-run UI and regression checks passed.
  Windows text output is canonical UTF-8/LF so resource hashes match other platforms.
- Android ARM64, API 36 emulator: automatic first run and regression checks passed;
  reopening with Wi-Fi/mobile data disabled also passed. The signed release APK
  was separately installed and opened. A physical Android device was not retested
  for this version.
- Arch ARM64 on Xiaomi Pad 5: native GTK first run completed in about 4 seconds;
  offline reopening and the game menu passed.
- Source corruption, TLS verification, cached sources, archive CRC, invalid flash
  input and preservation of existing saves were checked in isolated tests.

All 13 manifest entries validate. CODE, DATA, fonts, strings, original DLS,
effect metadata and the five played PCM sounds are byte-identical to the working
reference. The minimal SF2 is a different intermediate container with identical
played output; the legacy full bank remains supported for migration.

These tests are not exhaustive proof of every game state or hardware combination.
Linux x86_64 gameplay and physical Android 1.1.0 were not tested. The Release
includes the machine-readable `TEST-RESULTS.json`.

## 中文

首次启动使用空白用户目录，公开包的 `assets/` 只含图标与清单，没有借用已安装资源。
Mac、Windows x64 兼容环境、Android ARM64 模拟器、Arch ARM64 均通过自动获取后进入游戏的检查。
安卓另外验证了断网重开，并安装实际签名 Release APK。Arch 的 GTK 实测首次约 4 秒，离线重开通过。

全部 13 项清单验证通过；原版程序、字体、文字、DLS、音效元数据和五种播放用 PCM 与参考版本
逐字节一致。最小 SF2 是不同的中间容器，但生成 PCM 完全一致；也兼容迁移旧版完整音色库。
下载损坏、证书校验、缓存、CRC、错误固件和存档隔离检查通过。本次未在安卓实机或 Linux x86_64
上重测，也不代表穷尽全部状态。机器可读结果见 Release 内 `TEST-RESULTS.json`。
