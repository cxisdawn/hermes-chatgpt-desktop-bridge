# Architecture

本文说明 Hermes ChatGPT Desktop Bridge `1.8.0` 的组件、数据流和关键安全不变量。

## 组件

| 文件 | 作用 |
| --- | --- |
| `install.py` | 安装 Skill，给 Hermes CLI 注入 `/cg` 分发器和补全，并创建源码备份 |
| `hermes_cg_bridge.py` | WSL 侧传输层；创建私有临时提示词、转换 Windows 路径、启动 PowerShell、解析 Base64 回复 |
| `chatgpt_bridge.ps1` | Windows UI Automation；选择对话、验证输入、提交、等待生成并复制新回复 |
| `skill/chatgpt-collaboration/SKILL.md` | Hermes 可读的命令语义和行为约束 |

## 一次 `/cg` 的数据流

```text
Hermes conversation_history
        ↓ 找到最新非空 assistant 回复
compact prompt assembly
        ↓
WSL private temporary file
        ↓ wslpath
Windows PowerShell UI Automation
        ↓
existing ChatGPT conversation
        ↓ 等待 Stop control 消失或回复结构变化
single response-level Copy invocation
        ↓ Base64 over stdout
WSL Python transport
        ↓
~/.hermes/pastes/paste_N_HHMMSS.txt
        ↓
editable Hermes native paste reference
```

ChatGPT 对话本身保留项目上下文，所以桥接只发送本轮增量：Hermes 最新回复和可选的附加要求。

## 输入策略

桥接按以下顺序写入 ChatGPT composer：

1. 可写 `ValuePattern.SetValue`。
2. 可用的 `LegacyIAccessiblePattern.SetValue`。
3. 普通模式下，验证目标窗口和输入框焦点后使用剪贴板与键盘回退。
4. `--no-focus` 模式禁止第 3 步，前两步不可用时直接停止。

每次写入后都会从 accessibility tree 重新读取内容并验证。Chromium 可能改变 CR/LF 表示，因此验证忽略换行编码差异，但要求所有非换行字符完全一致。

## 提交和窗口恢复

桥接优先调用可见且启用的 Send 按钮 `InvokePattern`。找不到 Send 控件时，普通模式才会在已验证焦点后发送 Enter。

如果键盘回退使 ChatGPT 获得前台，提交清空 composer 的验证成功后，脚本立即恢复启动桥接前的前台窗口。最终清理阶段会再次尽力恢复。

## 回复完成检测

发送前只记录回复级 Copy 控件数量，不点击历史消息。提交后每 250 ms 只读轮询：

1. 检查 Stop/停止生成控件。
2. 检查回复级 Copy 控件数量是否增加。
3. 收到完成信号后等待 action row 稳定 2 秒。
4. 重新确认生成未继续。
5. 选择最底部可见的精确 `Copy`/`复制` 按钮。
6. 整个 `/cg` 只调用一次该按钮。

单次复制约束用于避免按钮变成“已复制”后，二次搜索误选上一条历史回复。

## 并发与恢复

正常桥接持有 Windows named mutex `Local\HermesCgBridge`，防止两个 Hermes 实例同时控制一个 ChatGPT composer。

`/cg --reset` 不启动 `chatgpt_bridge.ps1`，因此不获取该 mutex。它通过 UTF-16LE `-EncodedCommand` 启动独立清理器，只匹配当前 Windows 会话中命令行为 `-File ...chatgpt_bridge.ps1` 的 PowerShell 进程。

## Clipboard

脚本在第一次写入前保存 Windows clipboard data object，并在 `finally` 中尽力恢复。提示词、sentinel 和 ChatGPT 回复仍可能被 Windows 剪贴板历史、云同步或第三方管理器观察。

## 安全不变量

- 不读取 ChatGPT Cookie、Token、数据库或网络请求。
- 不猜测同名项目或对话；多个精确匹配直接失败。
- 不覆盖 ChatGPT 中已有草稿。
- 输入未验证时不提交。
- 提交未验证时不轮询回复。
- 每轮只调用一次回复级 Copy。
- 同时只允许一个正常桥接实例。
- 默认返回可编辑引用；只有显式 `--run` 自动提交给 Hermes。
- 临时提示词尽力删除；paste 文件使用用户私有权限。
