# Security Policy

## 数据流与信任边界

本项目跨越三个边界：WSL 中的 Hermes、Windows 桌面剪贴板与 UI Automation、已登录的 ChatGPT 云端对话。运行 `/cg` 等同于授权桥接把 Hermes 最新回复发送到当前或明确选择的 ChatGPT 对话。

项目不会读取或导出：

- ChatGPT Cookie、Session Token 或访问令牌；
- 浏览器或桌面客户端数据库；
- API Key、`.env` 文件或系统凭据；
- ChatGPT 私有网络接口。

## 本地保存内容

- ChatGPT 回复：`~/.hermes/pastes/paste_*.txt`。
- Hermes 源码备份：`~/.hermes/hermes-agent/*.cg-backup-*`。
- 临时提示词：由 `tempfile.NamedTemporaryFile` 创建，脚本结束时尽力删除。

粘贴目录会设置为 `0700`，新回复文件设置为 `0600`。这些文件不会自动过期；用户应根据自己的数据保留策略定期检查和清理。

## 剪贴板风险

自动化过程中，Windows 剪贴板会短暂保存发送给 ChatGPT 的提示词和复制回来的回复。脚本会在结束时尽力恢复运行前的完整剪贴板对象，但以下内容不受项目控制：

- Windows 剪贴板历史；
- 云剪贴板同步；
- 第三方剪贴板管理器；
- 其他进程对剪贴板的监听。

处理敏感数据前应关闭这些功能，或不要使用本项目传输该数据。

## 防止发送到错误对话

- 对项目名和对话标题使用大小写敏感的完整匹配。
- 同一标题匹配到多个控件时拒绝自动选择。
- 未指定 `--chat` 时使用当前打开的对话，因此运行前必须人工确认页面。
- 推荐关闭多余 ChatGPT 窗口，并在敏感任务中显式传入 `--project` 与 `--chat`。

UI Automation 无法提供与官方 API 相同的目标身份保证。首次使用或桌面客户端更新后，应先发送唯一、无敏感信息的测试口令。

## 遗留进程清理

`/cg --reset` 及其别名 `/cg --fuckyou` 会强制终止当前 Windows 登录会话中命令行为 `-File ...chatgpt_bridge.ps1` 的 PowerShell 进程，用于恢复被遗留桥接占用的互斥锁。它不会按进程名称批量终止普通 PowerShell，也不会跨 Windows 会话操作进程。

清理会中止正在进行的 `/cg` 传输，可能丢弃尚未返回 Hermes 的当轮回复，因此只应在确认桥接卡住或明确需要取消时使用。

## 安装器权限

`install.py` 会修改：

- `~/.hermes/hermes-agent/cli.py`
- `~/.hermes/hermes-agent/hermes_cli/commands.py`

安装器会先移除旧的标记补丁、构造新内容并执行 Python 编译检查，随后备份原文件再写入。定位不到预期代码锚点时会停止，不会猜测插入位置。

PowerShell 的 `-ExecutionPolicy Bypass` 仅作用于本次桥接子进程和明确指定的本地脚本，不修改系统级执行策略。

## 安全使用建议

1. 发布前审查仓库，不要提交 `.env`、日志、粘贴文件、备份、压缩包或终端截图。
2. 第一次运行使用无敏感唯一口令测试发送目标和返回内容。
3. 高风险任务使用默认 `/cg`，人工检查后按 Enter；不要使用 `--run`。
4. ChatGPT 或 Hermes 更新后重新执行连通测试。
5. 不要把密码、API Key、私钥、身份信息或无权外发的源码放入 Hermes 最新回复。
6. 从可信源码构建和安装；运行前可人工审查三个执行文件。

## 报告安全问题

请通过本 GitHub 仓库的 **Private vulnerability reporting / Security advisory** 私下报告。不要在公开 Issue 中粘贴凭据、私人对话、电脑路径或可识别个人身份的日志。

报告建议包含：

- 受影响版本；
- 最小复现步骤；
- 预期与实际行为；
- 已脱敏的错误信息；
- 风险影响与建议修复方式。
