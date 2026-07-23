# Publishing to GitHub

本文用于维护者发布首个 GitHub 仓库和 `v1.8.0` Release。不要把真实用户名、设备名、对话内容或本机日志写入仓库。

## 1. 发布前检查

在仓库根目录执行：

```bash
python3 -m py_compile install.py hermes_cg_bridge.py

python3 - <<'PY'
from pathlib import Path

p = Path("chatgpt_bridge.ps1")
b = p.read_bytes()
assert all(value < 128 for value in b), "PowerShell must remain ASCII-only"
text = b.decode("ascii")
assert text.count("Read-CopyButtonText -Button") == 1
print("release static checks passed")
PY

git diff --cached --check
git status --short
```

再人工确认：

- README 的安装命令可从空环境执行。
- `CHANGELOG.md` 顶部版本与 Skill `version` 一致。
- `.env`、日志、截图、paste 文件、备份和压缩包均未暂存。
- 所有错误示例已删除用户名、设备名和完整个人路径。
- Windows 实机已验证普通 `/cg`、`--reset` 和预期的 `--no-focus` 行为。

## 2. 创建首个提交

如果使用 GitHub-ready 源码压缩包，先初始化仓库并暂存文件：

```bash
git init -b main
git add .
git diff --cached --check
```

如果当前目录已经是本项目的 Git 工作区，则跳过初始化，只确认分支为 `main`、发布文件已经暂存。

然后配置自己的 Git 身份：

```bash
git config user.name "YOUR_GITHUB_NAME"
git config user.email "YOUR_GITHUB_EMAIL"
git commit -m "Initial release: v1.8.0"
```

不要提交他人的姓名或使用虚构邮箱冒充维护者。若希望隐藏公开邮箱，可使用 GitHub 提供的 `noreply` 地址。

## 3. 创建 GitHub 仓库

建议仓库名：

```text
hermes-chatgpt-desktop-bridge
```

在 GitHub 创建空公开仓库，不要再次添加 README、`.gitignore` 或 License。然后执行：

```bash
git remote add origin https://github.com/YOUR_GITHUB_NAME/hermes-chatgpt-desktop-bridge.git
git push -u origin main
```

如果使用 GitHub CLI：

```bash
gh repo create hermes-chatgpt-desktop-bridge \
    --public \
    --source=. \
    --remote=origin \
    --push
```

## 4. 创建 `v1.8.0` 标签

```bash
git tag -a v1.8.0 -m "Hermes ChatGPT Desktop Bridge v1.8.0"
git push origin v1.8.0
```

在 GitHub Releases 中选择该标签，标题使用：

```text
v1.8.0 — reset recovery and foreground-safe interaction
```

Release 内容可直接摘取 `CHANGELOG.md` 的 `1.8.0` 部分，并附上源码压缩包 SHA256。

## 5. GitHub 设置

建议启用：

- Issues；
- Private vulnerability reporting；
- 自动删除已合并分支；
- `main` 分支保护；
- 要求 Pull Request 才能合并；
- 至少一次状态检查通过。

不要在公开 Issue 中处理安全漏洞或包含私人对话的日志；按 `SECURITY.md` 引导到 Security Advisory。

## 6. 后续版本

行为变化时同时更新：

1. `skill/chatgpt-collaboration/SKILL.md` 的 `version`；
2. `CHANGELOG.md`；
3. README 的当前版本和兼容表；
4. 涉及的新测试与排障说明；
5. Git tag 和 GitHub Release。

保持版本标签、Skill 元数据和文档版本完全一致。
