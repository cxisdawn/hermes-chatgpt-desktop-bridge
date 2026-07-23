# Contributing

感谢改进 Hermes ChatGPT Desktop Bridge。该项目依赖桌面 accessibility tree，提交修改时请优先保证目标选择、输入验证和数据隐私，而不是扩大自动化范围。

## 开发环境

- Windows 10/11 + WSL2。
- Windows PowerShell 5.1。
- Python 3.11+。
- Hermes Agent 本地源码副本。
- ChatGPT Windows 桌面端，使用 `--force-renderer-accessibility` 启动。

建议用专用测试 HOME，避免修改日常 Hermes：

```bash
export HOME=/path/to/disposable-test-home
python3 install.py
```

测试 HOME 需要包含最小 Hermes 文件：

```text
~/.hermes/hermes-agent/cli.py
~/.hermes/hermes-agent/hermes_cli/commands.py
```

## 修改规则

- `chatgpt_bridge.ps1` 必须保持 ASCII-only，以兼容 Windows PowerShell 5.1 编码行为。
- 中文 UI 名称应使用 UTF-8 Base64，在运行时解码。
- 不得读取 Cookie、Token、浏览器数据库、客户端请求或私有接口。
- 不得自动覆盖 ChatGPT composer 草稿。
- 未验证输入和提交时不得继续。
- 每轮最多调用一次回复级 Copy。
- 同名项目或对话不得猜测选择。
- 新生成的 paste 文件必须为 `0600`，目录为 `0700`。
- 不要提交日志、截图、paste 文件、备份、`.env` 或个人路径。

## 本地检查

```bash
python3 -m py_compile install.py hermes_cg_bridge.py

python3 - <<'PY'
from pathlib import Path
p = Path("chatgpt_bridge.ps1")
b = p.read_bytes()
assert all(value < 128 for value in b), "PowerShell must remain ASCII-only"
text = b.decode("ascii")
assert text.count("Read-CopyButtonText -Button") == 1
print("static checks passed")
PY
```

在 WSL 中运行 `python3 install.py` 会额外调用 Windows PowerShell Parser。完成后必须测试卸载：

```bash
python3 install.py --uninstall
```

## 实机回归

至少验证：

1. `/c` 能补全 `/cg` 和全部选项。
2. `/cg 请只回复：BRIDGE_OK` 只发送一次、只复制一次并生成 paste reference。
3. paste 文件内容与 ChatGPT 回复一致。
4. ChatGPT 有草稿时安全拒绝。
5. `/cg --reset` 在有无遗留进程时均能返回。
6. `/cg --no-focus` 成功后台输入，或在只读 TextPattern 客户端上安全失败。
7. 普通键盘回退提交后立即恢复原前台窗口。
8. `--project`、`--chat` 精确选择和同名拒绝。

## Pull Request

PR 请保持单一主题，并说明：

- 问题和最小复现步骤；
- Windows、WSL、Hermes、ChatGPT 版本；
- 修改的安全不变量；
- 静态、安装、卸载和实机测试结果；
- 是否改变 README、Skill 或 Changelog。

公开内容必须脱敏。安全漏洞请按 [SECURITY.md](SECURITY.md) 私下报告。
