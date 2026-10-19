# Third-party components / 第三方组件

The newly written host is MIT licensed. Dependencies and original game data are separate:

| Component | Use | License / ownership |
| --- | --- | --- |
| [Unicorn](https://github.com/unicorn-engine/unicorn/tree/2.1.4) | ARM/Thumb execution | GPL-2.0; consult upstream for the engine and bindings |
| [Pillow](https://github.com/python-pillow/Pillow) | Pixel framebuffer | HPND; see upstream license |
| GTK / PyGObject / Cairo | Linux interface | Their respective upstream licenses |
| [PyObjC](https://github.com/ronaldoussoren/pyobjc) | macOS interface | MIT |
| [Chaquopy](https://chaquo.com/chaquopy/) | Android Python runtime | Consult its distribution licenses |
| [TinySoundFont](https://github.com/schellingb/TinySoundFont) | Offline effect rendering | MIT; header notice and license in audio-source/ |
| Snake Xenzia binary, bitmap fonts, icon, text and sound samples | Original game content, supplied separately | Nokia / respective rights holders; not licensed by this repository |

The repository does not contain firmware, original game binaries, disassembly,
Nokia media assets, personal saves, signing keys or prebuilt packages containing
those assets. Asset hashes describe the supported extraction; they are not the
assets themselves. The public release is the compatibility-layer source.

本仓库开源的是新编写的兼容层和各平台界面，不包含 Nokia 固件、原版程序、
字体、图标、音效采样或反汇编。原版资源需自行提供并导入，资源校验值不代表
资源授权。第三方组件遵循各自许可证；本仓库的 MIT 许可不会替代这些许可。
