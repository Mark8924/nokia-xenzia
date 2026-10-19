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

The repository does not automatically download or decrypt firmware. Importing
requires an already extracted asset directory matching the manifest; extraction
and resource ownership are separate from building this host. The audio-source
directory documents the original DLS/SF2 sampling pipeline but contains no Nokia
sample bank. No original game C/C++ source was recovered.

支持的版本固定为 RH-93 7.02，并非任意 Nokia 固件都能直接运行。清单记录了
当前兼容的提取结果。固件解密、NIFF/PPM 拆分和资源提取需要另行完成；仓库提供的
导入器只负责校验并复制已提取的文件。没有声称恢复原游戏 C/C++ 源码。
