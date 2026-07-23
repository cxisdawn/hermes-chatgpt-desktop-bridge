# Troubleshooting

排障前先确认：Windows 已解锁、ChatGPT 处于普通 `Chat` 页面、只保留一个 ChatGPT 主窗口、composer 没有草稿。

## `/c` 没有 `/cg`

Hermes 仍在使用安装前的命令注册表，或者 `hermes update` 覆盖了补丁。

```bash
cd hermes-chatgpt-bridge
python3 install.py
```

完全退出所有 Hermes 进程后重新启动。

## `Cannot find the Chat composer`

通常是 accessibility 未启用，或者当前页面是 Codex/Work 而不是普通 Chat。

在 Windows PowerShell 重新启动：

```powershell
Get-Process ChatGPT -ErrorAction SilentlyContinue | Stop-Process
$package = Get-AppxPackage OpenAI.Codex
$exe = Join-Path $package.InstallLocation "app\ChatGPT.exe"
Start-Process -FilePath $exe -ArgumentList "--force-renderer-accessibility"
```

然后切到普通 `Chat` 页面。

## `Another /cg bridge is already running`

上一次 Hermes 或终端异常退出，旧 PowerShell 仍在等待。

```text
/cg --reset
```

或使用兼容别名：

```text
/cg --fuckyou
```

若当前命令仍占用 Hermes 输入，先按 `Ctrl+C`。清理输出为 `0` 表示没有遗留进程，也是正常结果。

## `Background composer input is unavailable`

`--no-focus` 工作正常，但当前 ChatGPT composer 只暴露只读 `TextPattern`，没有可写 `ValuePattern` 或 `LegacyIAccessiblePattern`。

使用普通模式：

```text
/cg 请只回复：NORMAL_MODE_OK
```

ChatGPT 可能在粘贴和提交阶段短暂获得前台，但提交验证后应立即返回原窗口。生成和复制阶段不需要保持 ChatGPT 前台。

## `composer already contains a draft`

桥接保护 ChatGPT 中未发送的内容，不会自动覆盖。发送、保存或清空草稿后重试。

如果输入框看起来为空仍报错，确保使用 `1.6.2+`。旧版未处理 Chromium 在 placeholder 后附加的换行。

## `composer verification failed`

桥接已经停止且未发送消息。可能原因：

- ChatGPT 在粘贴时重建了 accessibility tree；
- 用户同时操作鼠标键盘；
- 剪贴板被其他软件锁定；
- 客户端更新改变了 contenteditable 行为。

保持窗口稳定后重试。`1.6.4+` 已容忍 Chromium 折叠 Markdown 连续换行，但所有非换行字符仍必须一致。

## 找不到项目或对话

- 展开 ChatGPT 侧边栏。
- 使用完整、大小写一致的标题。
- 标题含空格时加引号。
- 同名项目或对话只能保留一个可见匹配。
- 最稳定的方式是手动打开目标对话，然后不传 `--project` 和 `--chat`。

## 一直等待新回复

确认 ChatGPT 已完成生成且没有继续/停止按钮。不要在等待期间切换 ChatGPT 对话、重新生成、编辑消息或滚动到其他历史位置。

需要取消时：

1. 在 Hermes 按 `Ctrl+C`。
2. 返回提示符后运行 `/cg --reset`。
3. 在 ChatGPT 确认目标对话和空 composer。
4. 使用唯一口令重试。

## 连续复制历史回复或返回旧回复

这是 `1.6.x` 的二次复制稳定性逻辑导致的问题。安装 `1.7.0+`。当前版本在发送前不复制历史消息，生成完成后只调用一次最底部回复级 Copy。

## PowerShell 乱码或 ParserError

`chatgpt_bridge.ps1` 必须保持 ASCII-only。不要用会加入中文字符串或改变编码的编辑器保存它。重新下载原始仓库并运行安装器；安装器会在写入 Hermes 前调用 Windows PowerShell Parser。

## 安装时提示 PowerShell `path` 为空

这是 `1.6.0` 的参数传递问题。使用 `1.6.1+`；新版本通过 UTF-16LE `-EncodedCommand` 传递 parser 路径。

## 输入框出现引用但 Hermes 不理解

不要移动或删除引用对应的 paste 文件。在引用后增加明确要求，例如：

```text
请把以上内容作为 ChatGPT 的审查意见，并结合当前项目继续执行。
```

然后按 Enter，让 Hermes 正常展开引用。

## 提交 Issue 前收集信息

请先脱敏，不要提交用户名、电脑名、对话内容、凭据或完整本机路径。

```powershell
wsl --version
Get-AppxPackage | Where-Object {$_.Name -match "OpenAI|ChatGPT"} |
    Select-Object Name, Version
```

```bash
hermes --version
python3 --version
head -n 8 ~/.hermes/skills/chatgpt-collaboration/SKILL.md
```

Issue 应包含：最小复现命令、预期行为、实际错误、是否扩展屏、普通模式或 `--no-focus`、是否指定项目/对话。
