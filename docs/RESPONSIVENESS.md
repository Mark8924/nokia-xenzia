# Responsiveness / 响应性修复

## English

The original program measures the work in a frame and subtracts it from the next
requested timer delay. The previous host advanced its game clock only by that
remaining delay. Rendering cost therefore disappeared from guest time; as a snake
grew, the simulated clock fell further behind wall time. Real-time frames now
include their work in the guest clock, and GUI hosts recheck the timer deadline
after drawing and saving. Offline deterministic tests still use logical time.

Native helpers batch canvas commands and implement the same allocator API. They
contain no game program or assets. The unchanged Pillow canvas replays commands
in order, including alpha blending and fonts. Tests compare every pixel, all guest
RAM arenas, allocator blocks and free lists against the Python-only reference.
The original instruction count and execution deadline remain finite.

Sound commands reach each host's audio API at the original sound call, before
later drawing. The Linux worker preloads the original PCM and keeps only the
latest pending command on its monophonic channel.

GTK defers focus-loss pause briefly and cancels it when focus returns. The delayed
callback checks actual window activity. Genuine focus loss still pauses play;
held Select/Back keys cannot immediately toggle a new game back to its menu.

On the Xiaomi Pad 5 test device, a 100-segment stress frame dropped from about
264 ms to 62 ms. At default speed 4, both the short and 100-segment runs advanced
seven grid cells in about 2.2 seconds. These measurements describe that device,
not a performance guarantee for every host.

## 中文

原程序会把本帧耗时从下一次等待时间中扣除，但旧运行层的时钟只累计了剩下的
等待时间，漏掉了绘制耗时。蛇越长，漏算越多。现在实时运行会补齐这部分时间，
界面绘制、保存之后也会重新检查定时器截止时间。离线回归测试仍可用确定性时钟。

本机助手只批处理绘图接口和实现同样的内存分配接口，不含游戏程序或素材。
绘图仍按原顺序交给同一个 Pillow 画布。测试逐像素对比画面，并对比全部游戏
RAM、已分配块及空闲块；原有指令数量和运行期限保护仍保留。

音效在原程序调用声音接口时立即提交，不等待后续绘制。Linux 音频线程预加载
原版 PCM，单声道只保留最新待播放指令。短暂失焦后若已恢复焦点，不会再把新游戏
误暂停；真正切走仍正常暂停，按住选择／返回键也不会重复开关。
