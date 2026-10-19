# Supported original program / 支持的原版程序

- Device family: Nokia 1110i / 1112, RH-93.
- Firmware: 7.02, dated 2007-12-10.
- NAI image: `rh930_nai7.02ej`, first NIFF application record, Snake Xenzia.
- CODE length: 24,124 bytes; DATA length: 436 bytes.
- CPU: big-endian ARMv4T/Thumb, CODE loaded at 0x8000.
- Original INFO display size: 96×65.
- Required extracted file names and hashes: `assets/manifest.json`.

Useful original-format research:

- [DCT4Crypt](https://github.com/g3gg0/DCT4Crypt): DCT4 firmware decoding research.
- [TriX](https://github.com/g3gg0/TriX): Nokia firmware/PPM tools and format references.
- [nokia-recomp](https://github.com/sp00nznet/nokia-recomp): related original-program research.
- [Unicorn](https://github.com/unicorn-engine/unicorn/tree/2.1.4): CPU execution engine.

## Automatic on-device preparation

First launch fetches the public [RH-93 7.02 firmware archive](https://firmware.center/firmware/Nokia/1110i%20%281112%29/Flash%20Files/RH-093%20v.07.02%201110i%201112.rar)
using HTTPS with certificate verification enabled.

- Archive size: 3,700,384 bytes.
- SHA-256: `aeae974329c84a51882ff3956a0302228ae207cbeb1df23a7071ba85ebe0059f`.
- Only the two required stored RAR records are read, with CRC checks. No external
  unpacker is needed; the unrelated compressed PM record is skipped.
- `dct4_format.py` decodes the supported ranges, based on the MIT-licensed
  [nokia-recomp](https://github.com/sp00nznet/nokia-recomp) format implementation.
- `auto_assets.py` extracts CODE, DATA, text, fonts and the original DLS samples.
- `audio_layout.py` builds a three-voice SF2 from those samples and functional
  instrument parameters. Absolute sample positions preserve the reference
  interpolation. TinySoundFont renders the five effects locally.
- The new minimal SF2 and the earlier full SF2 have different container hashes;
  both are accepted for migration. **All five played PCM effects are byte-identical**,
  as are CODE, DATA, fonts, strings, DLS and the effect metadata.
- `assets/manifest.json` validates all 13 required files before atomic installation.
  Unverified downloads never become active assets. Saves and settings are separate.

No Nokia firmware, game program, sample bank or rendered effect is shipped in
public packages. A successful first launch caches the verified source locally;
future launches use the prepared resources offline. No original C/C++ game source
was recovered. The phone DSP and physical speaker are not emulated.

## 中文

首次启动自动通过验证证书的 HTTPS 获取上面固定版本的公开固件，并核对大小和 SHA-256。
程序读取两个未压缩的 RAR 记录，检查 CRC，解码指定范围并提取游戏程序、文字、字体和音色。
不需要安装解压器或编译器。TinySoundFont 在本机生成播放用音效。

新版最小 SF2 与旧版完整 SF2 的容器不同，清单兼容两者；**五种实际播放的 PCM 音效逐字节一致**，
程序、字体、文字、原 DLS 和音效元数据也一致。全部 13 项校验成功后才安装资源，失败不替换现有资源。
存档、设置不会混入或被覆盖。公开包不携带固件及原版程序、字体、音效，后续启动可离线使用。
没有恢复原游戏 C/C++ 源码，也不宣称完全模拟原机 DSP 和喇叭。
