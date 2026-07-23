#!/usr/bin/env python3
"""WSL-side transport for the Windows ChatGPT desktop UI bridge."""

from __future__ import annotations

import base64
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


PREFIX = "CG_BRIDGE_B64:"


RESET_SCRIPT = r'''$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$currentSessionId = (Get-Process -Id $PID).SessionId
$targets = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.SessionId -eq $currentSessionId -and
            $_.Name -in @("powershell.exe", "pwsh.exe") -and
            $_.CommandLine -match '(?i)-File\s+.*chatgpt_bridge\.ps1(?:\s|"|$)'
        }
)
foreach ($target in $targets) {
    Stop-Process -Id $target.ProcessId -Force -ErrorAction Stop
}
Start-Sleep -Milliseconds 400
$remaining = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.SessionId -eq $currentSessionId -and
            $_.Name -in @("powershell.exe", "pwsh.exe") -and
            $_.CommandLine -match '(?i)-File\s+.*chatgpt_bridge\.ps1(?:\s|"|$)'
        }
)
if ($remaining.Count -gt 0) {
    throw "Failed to stop $($remaining.Count) stale ChatGPT bridge process(es)"
}
Write-Output "CG_RESET_OK:$($targets.Count)"
'''


def windows_path(path: Path) -> str:
    result = subprocess.run(
        ["wslpath", "-w", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.decode("utf-8", errors="replace").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hermes ChatGPT desktop bridge")
    parser.add_argument("--project", default="", help="ChatGPT project title")
    parser.add_argument("--chat", default="", help="Existing ChatGPT chat title")
    parser.add_argument(
        "--no-focus",
        action="store_true",
        help="Never use foreground keyboard input as a fallback",
    )
    parser.add_argument(
        "--reset",
        "--fuckyou",
        dest="reset",
        action="store_true",
        help="Stop stale Windows ChatGPT bridge processes",
    )
    return parser.parse_args()


def reset_bridges() -> int:
    encoded = base64.b64encode(RESET_SCRIPT.encode("utf-16-le")).decode("ascii")
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"无法清理 ChatGPT 桥接进程：{exc}", file=sys.stderr)
        return 1

    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    marker = next(
        (line.strip() for line in stdout.splitlines() if line.startswith("CG_RESET_OK:")),
        "",
    )
    if completed.returncode != 0 or not marker:
        print(f"清理 ChatGPT 桥接进程失败：{stderr or stdout.strip()}", file=sys.stderr)
        return 1
    count = marker.split(":", 1)[1]
    print(f"已终止 {count} 个遗留桥接进程，互斥锁已释放")
    return 0


def main() -> int:
    args = parse_args()
    if args.reset:
        return reset_bridges()

    prompt = sys.stdin.read()
    if not prompt.strip():
        print("桥接输入为空", file=sys.stderr)
        return 2

    bridge_dir = Path(__file__).resolve().parent
    ps_script = bridge_dir / "chatgpt_bridge.ps1"
    if not ps_script.is_file():
        print(f"找不到 PowerShell 桥接脚本：{ps_script}", file=sys.stderr)
        return 2

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="hermes-cg-",
            suffix=".txt",
            delete=False,
        ) as handle:
            handle.write(prompt)
            temp_path = Path(handle.name)

        command = [
            "powershell.exe",
            "-NoProfile",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            windows_path(ps_script),
            "-InputFile",
            windows_path(temp_path),
            "-TimeoutSeconds",
            "600",
        ]
        if args.project:
            command.extend(["-ProjectTitle", args.project])
        if args.chat:
            command.extend(["-ChatTitle", args.chat])
        if args.no_focus:
            command.append("-NoFocusFallback")

        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=660,
            check=False,
        )
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()

        encoded = None
        for line in stdout.splitlines():
            if line.startswith(PREFIX):
                encoded = line[len(PREFIX) :].strip()

        if completed.returncode != 0 or not encoded:
            detail = stderr or stdout.strip() or f"PowerShell 退出码 {completed.returncode}"
            print(f"ChatGPT 桥接失败：{detail}", file=sys.stderr)
            return 1

        try:
            reply = base64.b64decode(encoded, validate=True).decode("utf-8")
        except Exception as exc:
            print(f"无法解析 ChatGPT 回复：{exc}", file=sys.stderr)
            return 1

        sys.stdout.write(reply)
        return 0
    except subprocess.TimeoutExpired:
        print("ChatGPT 桥接总等待时间超时", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"缺少所需命令：{exc.filename}", file=sys.stderr)
        return 1
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
