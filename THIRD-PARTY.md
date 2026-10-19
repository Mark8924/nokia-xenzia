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
| [nokia-recomp](https://github.com/sp00nznet/nokia-recomp) | DCT4 format decoding algorithm adaptation | MIT; third_party/nokia-recomp-LICENSE |
| [certifi](https://github.com/certifi/python-certifi) | Bundled public Mozilla CA roots for verified HTTPS | MPL-2.0; certs/LICENSE |
| Original black-and-white application icon (`assets/icon.png`) | Included application icon, unchanged from the initial local version | Nokia / respective rights holders; not covered by MIT |
| Snake Xenzia binary, bitmap fonts, text and sound samples | Original game content, obtained on-device | Nokia / respective rights holders; not licensed by this repository |

The repository does not contain firmware, original game binaries, disassembly,
Nokia game media (apart from the application icon), personal saves, signing keys
or prebuilt packages containing the game data. Asset hashes describe the supported extraction; they are not the
assets themselves. The public release includes compiled hosts and matching host
source. The exact Unicorn 2.1.4 upstream source and its license files are supplied
alongside the binaries in the same Release. Python bindings are adjusted only by
the loader-path substitution documented in `tools/prepare.py`.

本仓库开源的是新编写的兼容层和各平台界面，不包含 Nokia 固件、原版程序、
字体、音效采样或反汇编。应用图标沿用最初的黑白原版，其权利归原权利人，
不属于 MIT 许可范围。其余原版资源由首次启动自动获取并校验，资源校验值不代表
资源授权。第三方组件遵循各自许可证；本仓库的 MIT 许可不会替代这些许可。
