# Arch validation — 2026-10-19 / Arch 验证

## English

The updated GTK host was checked on Xiaomi Pad 5, Arch Linux ARM. The installed
original resources matched all 13 manifest entries. The user's saved game and
settings were unchanged by the update and isolated checks.

- Fresh GTK startup opens the game menu at default speed 4.
- Seven original sound-command parameter sets match the expected instrument
  mapping and PCM hashes, with release tails and no hard clipping.
- Buffered Up / Left / Down input executes in order without advancing the
  simulation merely to process input.
- Automated gameplay eats 15 foods, checks replacement positions and large-food
  frames, and resumes from a saved game. All 85 framebuffer comparisons match.
- Four between-level transitions retain their canvas for 61 frames each and
  resume gameplay; the final campaign completion returns to the menu.
- Optional intro, skipping, preference persistence, autosave and closing during
  the intro preserve the actual saved game. The intro produces 53 unique frames.

The startup fixture previously assumed one point per food. Since the original
game scores according to speed, it now targets three foods at the selected speed
instead of a fixed score of three. Game scoring itself was not changed.

These are automated checks. They do not claim exhaustive gameplay coverage or
subjective verification of audio playback on every device.

## 中文

已在小米平板 5 的 Arch Linux ARM 上检查更新后的 GTK 程序，13 项原版资源均与
清单匹配。更新和隔离测试未修改用户的实际存档及设置。

- 新用户启动直接进入菜单，默认速度为 4。
- 七组原版音效参数的乐器映射、PCM 校验值、尾音和削波检查通过。
- 快速连续方向输入保持顺序，不靠快进游戏处理按键。
- 自动游玩吃掉 15 个食物，检查食物换位、大食物和读档继续；85 次画面比较一致。
- 四段关间动画各保持 61 帧，完成后恢复游戏，最终通关返回菜单。
- 开场动画、跳过、设置保存、自动存档及播放中退出均保留实际进度；开场有 53 个不同画面。

旧启动测试固定期待“吃三个食物得三分”，现已适配原版随速度计分的逻辑。
游戏计分没有修改。这些结果属于自动检查，不代表穷尽所有游戏状态或验证所有设备的听感。
