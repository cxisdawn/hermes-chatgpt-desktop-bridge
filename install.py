#!/usr/bin/env python3
"""Install or remove the /cg bridge in a local Hermes Agent checkout."""

from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BEGIN = "        # HERMES_CG_BRIDGE_BEGIN\n"
END = "        # HERMES_CG_BRIDGE_END\n"
COMMAND_BEGIN = "    # HERMES_CG_COMMAND_BEGIN\n"
COMMAND_END = "    # HERMES_CG_COMMAND_END\n"

COMMAND_PATCH = '''    # HERMES_CG_COMMAND_BEGIN
    CommandDef(
        "cg",
        "Send the latest Hermes reply to ChatGPT and prefill an editable draft",
        "Tools & Skills",
        args_hint="[--project title] [--chat title] [--no-focus] [--show|--run] [instruction]",
        subcommands=("--project", "--chat", "--no-focus", "--show", "--run", "--reset", "--fuckyou", "--help"),
        cli_only=True,
    ),
    # HERMES_CG_COMMAND_END
'''

PATCH = r'''        # HERMES_CG_BRIDGE_BEGIN
        elif canonical == "cg":
            # Send Hermes' latest assistant response to the ordinary ChatGPT
            # desktop Chat UI, then feed ChatGPT's answer through the normal
            # next-turn user-message path.
            import subprocess as _cg_subprocess
            import sys as _cg_sys
            import shlex as _cg_shlex
            from pathlib import Path as _CgPath

            _cg_parts = cmd_original.split(None, 1)
            _cg_raw_args = _cg_parts[1].strip() if len(_cg_parts) > 1 else ""
            try:
                _cg_tokens = _cg_shlex.split(_cg_raw_args)
            except ValueError as _cg_exc:
                _cprint(f"  [red]✗ /cg 参数格式错误：{_escape(str(_cg_exc))}[/red]")
                return True

            _cg_project = ""
            _cg_chat = ""
            _cg_show = False
            _cg_run = False
            _cg_no_focus = False
            _cg_reset = False
            if _cg_tokens in (["--help"], ["-h"]):
                _cprint("  /cg [instruction]")
                _cprint("  /cg --chat \"Chat title\" [instruction]")
                _cprint("  /cg --project \"Project\" --chat \"Chat\" [instruction]")
                _cprint("  /cg --run [selection options] [instruction]  # submit automatically")
                _cprint("  /cg --show [selection options] [instruction] # print only")
                _cprint("  /cg --no-focus [selection options] [instruction] # never use foreground keyboard fallback")
                _cprint("  /cg --reset  # stop stale bridge processes; --fuckyou is an alias")
                return True
            _cg_extra_tokens = []
            _cg_i = 0
            while _cg_i < len(_cg_tokens):
                _cg_token = _cg_tokens[_cg_i]
                if _cg_token in {"--project", "-p"}:
                    if _cg_i + 1 >= len(_cg_tokens):
                        _cprint("  [red]✗ --project 后需要项目标题[/red]")
                        return True
                    _cg_project = _cg_tokens[_cg_i + 1]
                    _cg_i += 2
                elif _cg_token in {"--chat", "-c"}:
                    if _cg_i + 1 >= len(_cg_tokens):
                        _cprint("  [red]✗ --chat 后需要对话标题[/red]")
                        return True
                    _cg_chat = _cg_tokens[_cg_i + 1]
                    _cg_i += 2
                elif _cg_token == "--show":
                    _cg_show = True
                    _cg_i += 1
                elif _cg_token == "--run":
                    _cg_run = True
                    _cg_i += 1
                elif _cg_token == "--no-focus":
                    _cg_no_focus = True
                    _cg_i += 1
                elif _cg_token in {"--reset", "--fuckyou"}:
                    _cg_reset = True
                    _cg_i += 1
                elif _cg_token == "--":
                    _cg_extra_tokens.extend(_cg_tokens[_cg_i + 1:])
                    break
                elif _cg_token.startswith("-"):
                    _cprint(f"  [red]✗ 未知 /cg 参数：{_escape(_cg_token)}[/red]")
                    return True
                else:
                    _cg_extra_tokens.extend(_cg_tokens[_cg_i:])
                    break
            _cg_extra = " ".join(_cg_extra_tokens).strip()
            if _cg_show and _cg_run:
                _cprint("  [red]✗ --show 和 --run 不能同时使用[/red]")
                return True

            _cg_bridge = (
                _CgPath.home()
                / ".hermes"
                / "skills"
                / "chatgpt-collaboration"
                / "scripts"
                / "hermes_cg_bridge.py"
            )
            if not _cg_bridge.is_file():
                _cprint(f"  [red]✗ 找不到 ChatGPT 桥接脚本：{_cg_bridge}[/red]")
                return True

            if _cg_reset:
                if (
                    _cg_project or _cg_chat or _cg_show or _cg_run
                    or _cg_no_focus or _cg_extra
                ):
                    _cprint("  [red]✗ --reset/--fuckyou 不能和其他参数或要求同时使用[/red]")
                    return True
                _cprint("  [dim]正在终止遗留的 ChatGPT 桥接进程…[/dim]")
                try:
                    _cg_reset_result = _cg_subprocess.run(
                        [_cg_sys.executable, str(_cg_bridge), "--reset"],
                        text=True,
                        stdout=_cg_subprocess.PIPE,
                        stderr=_cg_subprocess.PIPE,
                        timeout=20,
                        check=False,
                    )
                except _cg_subprocess.TimeoutExpired:
                    _cprint("  [red]✗ 清理桥接进程超时[/red]")
                    return True
                if _cg_reset_result.returncode != 0:
                    _cg_reset_error = (
                        _cg_reset_result.stderr or "未知错误"
                    ).strip()
                    _cprint(f"  [red]✗ {_escape(_cg_reset_error)}[/red]")
                    return True
                _cg_reset_output = (_cg_reset_result.stdout or "").strip()
                _cprint(f"  [green]✓ {_escape(_cg_reset_output)}[/green]")
                return True

            _cg_latest = ""
            for _cg_message in reversed(self.conversation_history or []):
                if _cg_message.get("role") == "assistant":
                    _cg_latest = _assistant_copy_text(
                        _cg_message.get("content", "")
                    ).strip()
                    if _cg_latest:
                        break

            if not _cg_latest:
                _cprint("  [red]✗ 没有找到可发送的 Hermes 最新回复[/red]")
                return True

            # Compact protocol: the persistent ChatGPT conversation already
            # carries collaboration context, so only send this turn's delta.
            _cg_prompt_parts = ["Hermes：", _cg_latest]
            if _cg_extra:
                _cg_prompt_parts.extend([
                    "",
                    "要求：",
                    _cg_extra,
                ])
            else:
                _cg_prompt_parts.extend(["", "请直接给出下一步指令。"])
            _cg_prompt = "\n".join(_cg_prompt_parts)

            _cprint("  [dim]正在发送 Hermes 最新回复到 ChatGPT…[/dim]")
            try:
                _cg_bridge_command = [_cg_sys.executable, str(_cg_bridge)]
                if _cg_project:
                    _cg_bridge_command.extend(["--project", _cg_project])
                if _cg_chat:
                    _cg_bridge_command.extend(["--chat", _cg_chat])
                if _cg_no_focus:
                    _cg_bridge_command.append("--no-focus")
                _cg_result = _cg_subprocess.run(
                    _cg_bridge_command,
                    input=_cg_prompt,
                    text=True,
                    stdout=_cg_subprocess.PIPE,
                    stderr=_cg_subprocess.PIPE,
                    timeout=660,
                    check=False,
                )
            except _cg_subprocess.TimeoutExpired:
                _cprint("  [red]✗ 等待 ChatGPT 回复超时[/red]")
                return True

            _cg_reply = (_cg_result.stdout or "").strip()
            if _cg_result.returncode != 0 or not _cg_reply:
                _cg_error = (_cg_result.stderr or "未知错误").strip()
                _cprint(f"  [red]✗ ChatGPT 桥接失败：{_escape(_cg_error)}[/red]")
                return True

            if _cg_show:
                _cprint("\n  [bold]ChatGPT reply:[/bold]")
                _cprint(f"  {_escape(_cg_reply)}")
                return True

            if _cg_run:
                # Explicit auto-run mode: process_loop consumes this one-shot
                # seed and routes it through self.chat(...) normally.
                self._pending_agent_seed = _cg_reply
                _cprint("  [green]✓ 已取得 ChatGPT 回复，正在交给 Hermes[/green]")
                return True

            # Default draft mode: store the full response using Hermes' native
            # paste-reference format. The composer stays compact and Hermes'
            # existing _expand_paste_references() restores the content on Enter.
            from datetime import datetime as _CgDateTime
            import os as _cg_os

            _cg_paste_dir = _CgPath.home() / ".hermes" / "pastes"
            try:
                _cg_paste_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                _cg_paste_dir.chmod(0o700)
                _cg_existing_numbers = []
                for _cg_existing_file in _cg_paste_dir.glob("paste_*_*.txt"):
                    try:
                        _cg_existing_numbers.append(
                            int(_cg_existing_file.name.split("_", 2)[1])
                        )
                    except (ValueError, IndexError):
                        pass

                _cg_paste_number = max(_cg_existing_numbers, default=0) + 1
                _cg_paste_stamp = _CgDateTime.now().strftime("%H%M%S")
                while True:
                    _cg_paste_file = _cg_paste_dir / (
                        f"paste_{_cg_paste_number}_{_cg_paste_stamp}.txt"
                    )
                    try:
                        _cg_fd = _cg_os.open(
                            _cg_paste_file,
                            _cg_os.O_WRONLY | _cg_os.O_CREAT | _cg_os.O_EXCL,
                            0o600,
                        )
                        with _cg_os.fdopen(_cg_fd, "w", encoding="utf-8") as _cg_handle:
                            _cg_handle.write(_cg_reply)
                        _cg_paste_file.chmod(0o600)
                        break
                    except FileExistsError:
                        _cg_paste_number += 1
                _cg_line_count = _cg_reply.count("\n") + 1
                _cg_draft = (
                    f"[Pasted text #{_cg_paste_number}: {_cg_line_count} lines "
                    f"→ {_cg_paste_file}]"
                )
            except OSError as _cg_paste_exc:
                _cprint(
                    f"  [red]✗ 无法创建 Hermes 粘贴文件："
                    f"{_escape(str(_cg_paste_exc))}[/red]"
                )
                return True

            # process_command runs on the background input thread, so mutate
            # prompt_toolkit's composer on its UI loop.
            def _cg_prefill_input():
                try:
                    _cg_buffer = self._app.current_buffer
                    _cg_buffer.text = _cg_draft
                    _cg_buffer.cursor_position = len(_cg_draft)
                    self._app.invalidate()
                except Exception as _cg_fill_exc:
                    _cprint(
                        f"  [red]✗ 无法回填 Hermes 输入框："
                        f"{_escape(str(_cg_fill_exc))}[/red]"
                    )

            _cg_loop = getattr(self._app, "loop", None) if self._app else None
            if _cg_loop is not None and _cg_loop.is_running():
                _cg_loop.call_soon_threadsafe(_cg_prefill_input)
            else:
                _cg_prefill_input()
            _cprint("  [green]✓ GPT 回复已作为 Hermes 粘贴引用填入；可追加要求后按 Enter[/green]")
        # HERMES_CG_BRIDGE_END
'''


def paths() -> tuple[Path, Path, Path]:
    source_dir = Path(__file__).resolve().parent
    hermes_dir = Path.home() / ".hermes" / "hermes-agent"
    target_skill_dir = Path.home() / ".hermes" / "skills" / "chatgpt-collaboration"
    return source_dir, hermes_dir, target_skill_dir


def validate_powershell_script(script_path: Path) -> None:
    """Parse the bridge with Windows PowerShell when installing from WSL."""
    powershell = shutil.which("powershell.exe")
    wslpath = shutil.which("wslpath")
    if not powershell or not wslpath:
        print("提示：当前环境不是 WSL，已跳过 Windows PowerShell 语法检查")
        return

    converted = subprocess.run(
        [wslpath, "-w", str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if converted.returncode != 0:
        detail = converted.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"无法转换 PowerShell 脚本路径：{detail}")
    windows_script = converted.stdout.decode("utf-8", errors="replace").strip()

    escaped_path = windows_script.replace("'", "''")
    parser_command = (
        "$utf8=[System.Text.UTF8Encoding]::new($false); "
        "[Console]::OutputEncoding=$utf8; $OutputEncoding=$utf8; "
        f"$path='{escaped_path}'; "
        "$tokens=$null; $errors=$null; "
        "[System.Management.Automation.Language.Parser]::ParseFile("
        "$path, [ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { "
        "$errors | ForEach-Object { [Console]::Error.WriteLine($_.Message) }; "
        "exit 1 }"
    )
    encoded_command = base64.b64encode(
        parser_command.encode("utf-16-le")
    ).decode("ascii")
    parsed = subprocess.run(
        [powershell, "-NoProfile", "-EncodedCommand", encoded_command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if parsed.returncode != 0:
        detail = parsed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"PowerShell 桥接脚本语法检查失败：{detail}")


def remove_marked_block(
    text: str,
    begin: str = BEGIN,
    end_marker: str = END,
) -> tuple[str, bool]:
    start = text.find(begin)
    if start < 0:
        return text, False
    end = text.find(end_marker, start)
    if end < 0:
        raise RuntimeError("发现不完整的 /cg 补丁标记，请停止并检查 Hermes 源码")
    end += len(end_marker)
    return text[:start] + text[end:], True


def install() -> None:
    source_dir, hermes_dir, target_skill_dir = paths()
    cli_path = hermes_dir / "cli.py"
    commands_path = hermes_dir / "hermes_cli" / "commands.py"
    if not cli_path.is_file():
        raise RuntimeError(f"找不到 Hermes cli.py：{cli_path}")
    if not commands_path.is_file():
        raise RuntimeError(f"找不到 Hermes commands.py：{commands_path}")

    skill_source = source_dir / "skill" / "chatgpt-collaboration" / "SKILL.md"
    if not skill_source.is_file():
        raise RuntimeError(f"找不到 Skill 定义：{skill_source}")

    powershell_source = source_dir / "chatgpt_bridge.ps1"
    if not powershell_source.is_file():
        raise RuntimeError(f"找不到 PowerShell 桥接脚本：{powershell_source}")
    validate_powershell_script(powershell_source)

    scripts_dir = target_skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill_source, target_skill_dir / "SKILL.md")
    for filename in ("chatgpt_bridge.ps1", "hermes_cg_bridge.py"):
        shutil.copy2(source_dir / filename, scripts_dir / filename)

    original = cli_path.read_text(encoding="utf-8")
    clean, already_installed = remove_marked_block(original)
    method_needle = "    def process_command(self, command: str) -> bool:\n"
    method_start = clean.find(method_needle)
    needle = '        elif canonical == "help":\n'
    needle_at = clean.find(needle, method_start) if method_start >= 0 else -1
    if method_start < 0 or needle_at < 0:
        raise RuntimeError("无法定位 process_command() 的 help 分支；Hermes 版本可能已变化")

    patched = clean[:needle_at] + PATCH + clean[needle_at:]
    compile(patched, str(cli_path), "exec")

    commands_original = commands_path.read_text(encoding="utf-8")
    commands_clean, command_already_installed = remove_marked_block(
        commands_original,
        COMMAND_BEGIN,
        COMMAND_END,
    )
    registry_anchor = "COMMAND_REGISTRY: list[CommandDef] = [\n"
    registry_at = commands_clean.find(registry_anchor)
    if registry_at < 0:
        raise RuntimeError("无法定位 commands.py 的 COMMAND_REGISTRY")
    registry_at += len(registry_anchor)
    commands_patched = (
        commands_clean[:registry_at]
        + COMMAND_PATCH
        + commands_clean[registry_at:]
    )
    compile(commands_patched, str(commands_path), "exec")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = cli_path.with_name(f"cli.py.cg-backup-{stamp}")
    commands_backup = commands_path.with_name(f"commands.py.cg-backup-{stamp}")
    shutil.copy2(cli_path, backup)
    shutil.copy2(commands_path, commands_backup)
    cli_path.write_text(patched, encoding="utf-8")
    commands_path.write_text(commands_patched, encoding="utf-8")

    action = "已更新" if (already_installed or command_already_installed) else "已安装"
    print(f"{action} Hermes /cg 桥接")
    print(f"Skill：{target_skill_dir}")
    print(f"CLI 备份：{backup}")
    print(f"补全注册表备份：{commands_backup}")
    print("请完全退出并重新运行 hermes，然后使用：/cg 或 /cg 附加要求")


def uninstall() -> None:
    _, hermes_dir, _ = paths()
    cli_path = hermes_dir / "cli.py"
    commands_path = hermes_dir / "hermes_cli" / "commands.py"
    if not cli_path.is_file():
        raise RuntimeError(f"找不到 Hermes cli.py：{cli_path}")
    if not commands_path.is_file():
        raise RuntimeError(f"找不到 Hermes commands.py：{commands_path}")

    original = cli_path.read_text(encoding="utf-8")
    clean, removed = remove_marked_block(original)
    commands_original = commands_path.read_text(encoding="utf-8")
    commands_clean, command_removed = remove_marked_block(
        commands_original,
        COMMAND_BEGIN,
        COMMAND_END,
    )
    if not removed and not command_removed:
        print("Hermes 源码中没有 /cg 补丁，无需卸载")
        return

    compile(clean, str(cli_path), "exec")
    compile(commands_clean, str(commands_path), "exec")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = cli_path.with_name(f"cli.py.before-cg-uninstall-{stamp}")
    commands_backup = commands_path.with_name(
        f"commands.py.before-cg-uninstall-{stamp}"
    )
    shutil.copy2(cli_path, backup)
    shutil.copy2(commands_path, commands_backup)
    cli_path.write_text(clean, encoding="utf-8")
    commands_path.write_text(commands_clean, encoding="utf-8")
    print(f"已移除 /cg 执行和补全注册；CLI 备份：{backup}")
    print(f"补全注册表备份：{commands_backup}")
    print("chatgpt-collaboration Skill 已保留；如需永久删除，请明确手动删除对应 Skill 目录。")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes /cg bridge installer")
    parser.add_argument("--uninstall", action="store_true", help="移除 cli.py 中的 /cg 补丁")
    args = parser.parse_args()

    try:
        if args.uninstall:
            uninstall()
        else:
            install()
    except Exception as exc:
        print(f"安装失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
