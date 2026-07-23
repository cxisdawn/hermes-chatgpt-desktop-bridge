# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [1.8.0] - 2026-07-23

### Added

- `/cg --reset`：从 Hermes 中终止当前 Windows 会话的遗留桥接进程并释放互斥锁。
- `/cg --fuckyou`：`--reset` 的兼容别名。
- `/cg --no-focus`：严格禁止前台键盘回退。
- 后台输入增加 `LegacyIAccessiblePattern.SetValue` 尝试。

### Changed

- 普通模式只在必要时短暂激活 ChatGPT，提交验证后立即恢复原前台窗口。
- 项目和对话导航后立即恢复原前台窗口。

### Security

- 清理命令仅匹配当前 Windows 会话中通过 `-File` 启动 `chatgpt_bridge.ps1` 的 PowerShell 进程。

## [1.7.0] - 2026-07-23

### Fixed

- 删除发送前复制旧回复的基线逻辑。
- 删除完成后的双重 Copy 稳定性检查。
- 每轮只调用一次最底部回复级 Copy，修复连续复制历史消息且不返回 Hermes。
- 扩大中英文 Stop 控件匹配，并在生成结束后等待 action row 稳定。

## [1.6.4] - 2026-07-23

- composer 验证容忍 Chromium TextPattern 折叠 Markdown 连续换行，同时继续逐字验证所有非换行字符。

## [1.6.3] - 2026-07-23

- composer 验证忽略 Chromium TextPattern 添加的尾部换行。

## [1.6.2] - 2026-07-23

- 正确识别带 accessibility 尾部换行的空 composer placeholder。

## [1.6.1] - 2026-07-23

- PowerShell parser 路径改用 UTF-16LE `-EncodedCommand` 传递。

## [1.6.0] - 2026-07-23

- 输入和提交后进行内容验证。
- 增加多显示器适配、named mutex 和 clipboard 恢复。

## [1.0.0] - 2026-07-22

- 初始 `/cg`、项目/对话选择、可编辑 paste reference、`--run`、`--show` 和命令补全。
