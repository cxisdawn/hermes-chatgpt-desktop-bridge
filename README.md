# Hermes ChatGPT Desktop Bridge

让 WSL 中的 Hermes Agent 通过 `/cg` 与 Windows ChatGPT 桌面端的现有对话协作。

桥接会把 Hermes 最新回复发送给 ChatGPT，等待新回复完成，再把完整内容保存为 Hermes 原生粘贴引用。你可以编辑要求后按 Enter，也可以选择自动提交。

```text
[Pasted text #7: 12 lines → /home/<user>/.hermes/pastes/paste_7_143025.txt]
```

项目使用 Windows UI Automation，不使用 Codex CLI、OpenAI API、Cookie、访问令牌或 ChatGPT 私有网络接口。它不会绕过账号限制，所有请求仍受 ChatGPT 产品策略约束。

> 当前版本：`1.8.0`。这是实验性桌面自动化，ChatGPT 或 Hermes 更新后可能需要重新适配。
## Demo / 使用演示

40-second demonstration of the complete Hermes–ChatGPT collaboration workflow.

40 秒演示：Hermes 输出发送至 ChatGPT，ChatGPT 回复自动返回 Hermes，并生成可编辑粘贴引用。

[demo](https://github.com/cxisdawn/hermes-chatgpt-desktop-bridge/issues/1#issue-4954945783)
## 核心能力

- `/cg`：发送 Hermes 最新回复，并把 ChatGPT 回复填入 Hermes 输入框。
- `/cg <要求>`：只追加本轮要求，不重复搬运完整历史。
- `--project`、`--chat`：继续指定的已有项目对话，不创建新对话。
- `--run`：跳过编辑，直接把 ChatGPT 回复提交给 Hermes。
- `--show`：只显示 ChatGPT 回复。
- `--reset`：在 Hermes 中终止遗留桥接并释放互斥锁。
- `--no-focus`：禁止前台键盘回退；不能完全后台输入时安全停止。
- 每轮只调用一次回复级“复制”，避免误复制历史消息。
- 回复文件权限为 `0600`，粘贴目录权限为 `0700`。

## 数据流


详细设计和安全不变量见 [Architecture](docs/ARCHITECTURE.md)。

## 兼容环境

以下环境用于开发和实机问题复现，不代表唯一可用组合：

| 组件 | 参考版本 |
| --- | --- |
| Windows | Build `10.0.26200.8875` |
| WSL | `2.7.8.0`，WSL2 |
| WSL Kernel | `6.18.33.1-1` |
| Linux | Ubuntu on WSL2 |
| Hermes Agent | `v0.17.0 (2026.6.19)` |
| Python | `3.11.15` |
| ChatGPT Windows app | Package `26.715.9868.0`，进程 `ChatGPT.exe` |
| PowerShell | Windows PowerShell 5.1-compatible |
| Bridge | `1.8.0` |

查看本机版本：

```powershell
wsl --version
Get-AppxPackage | Where-Object {$_.Name -match "OpenAI|ChatGPT"} |
    Select-Object Name, Version, InstallLocation
```

```bash
hermes --version
python3 --version
```

测试环境中的桌面包名是 `OpenAI.Codex`，但桥接操作的是应用中的普通 `Chat` 页面，不是 Codex 任务页面。

## 安装

### 1. 前置条件

- Windows 10/11 和 WSL2。
- Hermes 位于 `~/.hermes/hermes-agent/`。
- WSL 可调用 `python3`、`powershell.exe` 和 `wslpath`。
- Windows ChatGPT 桌面端已登录并打开普通 `Chat` 页面。
- 目标项目或对话标题在展开的侧边栏中可见。

### 2. 启用 ChatGPT accessibility

在 Windows PowerShell 执行：

```powershell
Get-Process ChatGPT -ErrorAction SilentlyContinue | Stop-Process

$package = Get-AppxPackage OpenAI.Codex
if (-not $package) {
    throw "未找到 OpenAI Windows 桌面应用，请先确认实际包名"
}

$exe = Join-Path $package.InstallLocation "app\ChatGPT.exe"
Start-Process -FilePath $exe -ArgumentList "--force-renderer-accessibility"
```

如果包名不是 `OpenAI.Codex`，使用“兼容环境”中的查询命令找到实际包名并替换。

### 3. 安装桥接

在 WSL 中进入仓库根目录：

```bash
cd hermes-chatgpt-bridge
python3 install.py
```

安装器会：

1. 安装 Skill 到 `~/.hermes/skills/chatgpt-collaboration/`。
2. 给 Hermes `cli.py` 注入 `/cg` 执行入口。
3. 给 `hermes_cli/commands.py` 注册命令补全。
4. 修改前创建带时间戳的源码备份。
5. 编译检查 Python，并在 WSL 中调用 Windows PowerShell Parser 检查脚本。
6. 任一检查失败时停止，不猜测 Hermes 源码位置。

完全退出旧 Hermes 进程后重新启动：

```bash
hermes
```

输入 `/c` 应看到 `/cg`；输入 `/cg ` 应看到各选项。

## 使用

### 继续当前对话

先在 ChatGPT 手动打开目标对话，然后在 Hermes 输入：

```text
/cg
```

默认发送的增量内容很短：

```text
Hermes：
<Hermes 最新回复>

请直接给出下一步指令。
```

### 添加本轮要求

```text
/cg 请检查实现是否安全，只给出下一步可执行修改
```

### 选择已有对话

```text
/cg --chat "Agent 架构审查" 请继续检查最新实现
```

指定项目中的对话：

```text
/cg --project "Agent Project" --chat "架构审查" 请给出下一步指令
```

短参数为 `-p` 和 `-c`。标题按完整名称精确匹配；含空格时必须加引号。目标必须在侧边栏中可见，同名目标超过一个时桥接会拒绝选择。

### 编辑后提交（默认，推荐）

ChatGPT 回复会填成原生引用：

```text
[Pasted text #7: 12 lines → /home/<user>/.hermes/pastes/paste_7_143025.txt]
```

在引用后补充要求，再按 Enter。Hermes 自带的 paste-reference handler 会读取完整文件。

### 自动提交或只查看

```text
/cg --run 请审查最新回复并给出下一步
/cg --show 请审查最新回复
```

涉及删除、发布或外部操作时，建议保留默认人工确认，不使用 `--run`。

### 清理遗留进程

```text
/cg --reset
```

兼容别名：

```text
/cg --fuckyou
```

清理命令绕过互斥锁，只终止当前 Windows 会话中以 `-File ...chatgpt_bridge.ps1` 启动的 PowerShell，不影响普通 PowerShell 窗口。若当前 `/cg` 正在阻塞，先按 `Ctrl+C` 返回 Hermes 提示符。

### 前台与严格后台模式

普通 `/cg` 优先尝试后台 UI Automation 写入。若当前 ChatGPT 只暴露只读 `TextPattern`，会短暂激活 ChatGPT 完成粘贴和发送，并在提交验证成功后立即切回原窗口；生成和复制阶段不需要 ChatGPT 保持前台。

严格禁止前台回退：

```text
/cg --no-focus 请审查最新回复
```

如果客户端没有可写的 `ValuePattern` 或 `LegacyIAccessiblePattern`，该模式会安全返回 `Background composer input is unavailable`。这表示客户端能力不支持完全后台输入，不是桥接故障。

### 帮助

```text
/cg --help
```

## 首次测试

不要先发送源码或秘密信息。让 Hermes 产生一条普通回复，再运行：

```text
/cg 请忽略其他内容，只回复：GPT_BRIDGE_OK_2026
```

出现粘贴引用后，在另一 WSL 终端检查：

```bash
latest=$(ls -t "$HOME"/.hermes/pastes/paste_*.txt | head -n 1)
printf 'File: %s\n' "$latest"
cat "$latest"
```

文件内容应为：

```text
GPT_BRIDGE_OK_2026
```

然后在 Hermes 中对引用按 Enter，确认 Hermes 能展开并处理它。

## 常见问题

| 现象 | 标准处理 |
| --- | --- |
| `/c` 没有 `/cg` | 完全退出 Hermes，重新运行 `python3 install.py` 后启动 |
| `Cannot find the Chat composer` | 用 accessibility 参数重启应用，并切到普通 `Chat` 页面 |
| `Another /cg bridge is already running` | 运行 `/cg --reset`；若仍阻塞先按 `Ctrl+C` |
| `Background composer input is unavailable` | 改用普通 `/cg`，允许提交阶段短暂切换窗口 |
| 找不到项目或对话 | 展开侧边栏并使用完整标题；含空格时加引号 |
| `hermes update` 后 `/cg` 消失 | 重新运行安装器并重启 Hermes |
| 多个 ChatGPT 窗口 | 只保留目标窗口后重试 |

完整错误对照和诊断命令见 [Troubleshooting](docs/TROUBLESHOOTING.md)。

## 安全与隐私

使用前请阅读 [Security Policy](SECURITY.md)。重要边界：

- `/cg` 会把 Hermes 最新回复发送到已登录的 ChatGPT 云端对话。
- Windows 剪贴板会短暂包含提示词和回复；脚本会尽力恢复原对象，但无法阻止剪贴板历史或第三方工具记录。
- 回复保存在 `~/.hermes/pastes/`，不会自动过期。
- 项目不读取 Cookie、账号令牌、客户端数据库或私有网络接口。
- 默认模式要求人工按 Enter；高风险任务不要使用 `--run`。

## 更新与卸载

更新：

```bash
git pull
python3 install.py
```

重复安装会替换已有标记补丁，不会重复插入。

卸载 Hermes `/cg` 入口和补全：

```bash
python3 install.py --uninstall
```

卸载会保留 Skill、paste 文件和备份，避免自动删除用户数据。

## 开发与发布

- 贡献说明：[CONTRIBUTING.md](CONTRIBUTING.md)
- 版本记录：[CHANGELOG.md](CHANGELOG.md)
- 架构说明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- GitHub 发布：[docs/PUBLISHING.md](docs/PUBLISHING.md)
- 安全报告：[SECURITY.md](SECURITY.md)

发布到 GitHub 前至少运行：

```bash
python3 -m py_compile install.py hermes_cg_bridge.py
python3 install.py
python3 install.py --uninstall
git status --short
```

安装和卸载测试应在专用 Hermes 测试副本中进行，不要为发布测试破坏日常环境。

## 仓库结构

```text
hermes-chatgpt-bridge/
├── .github/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PUBLISHING.md
│   └── TROUBLESHOOTING.md
├── skill/chatgpt-collaboration/SKILL.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── chatgpt_bridge.ps1
├── hermes_cg_bridge.py
└── install.py
```

## 实现边界

- 这是 UI Automation 适配层，不是 OpenAI 官方集成。
- 只支持继续已有对话，不自动创建项目或新对话。
- 当前依赖中英文 ChatGPT accessibility 名称和客户端结构。
- 安装器会修改 Hermes 本地源码；Hermes 更新后可能需要重新安装或适配。
- 推荐只保留一个可见 ChatGPT 主窗口。
- 完全后台输入取决于客户端是否暴露可写 accessibility pattern。

## License

[MIT](LICENSE)。本项目与 OpenAI、ChatGPT、Hermes Agent 的官方团队无隶属或背书关系；相关名称和商标归各自权利人所有。
