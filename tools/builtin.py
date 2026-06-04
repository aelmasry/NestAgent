"""Built-in tools shipped with NestAgent."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import Any

from tools.base import Tool, ToolResult


class EchoTool(Tool):
    name = "echo"
    description = "Return input unchanged (smoke test)."

    def run(self, **kwargs: Any) -> ToolResult:
        message = kwargs.get("message", "")
        return ToolResult(success=True, output={"message": message}, message="ok")


class EnvironmentCheckTool(Tool):
    name = "environment_check"
    description = "Report Python, pip, git, and Ollama CLI availability."

    def run(self, **kwargs: Any) -> ToolResult:
        report = {
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "pip": shutil.which("pip3") or shutil.which("pip"),
            "git": shutil.which("git"),
            "ollama": shutil.which("ollama"),
            "platform": platform.platform(),
        }
        ollama_version = None
        if report["ollama"]:
            try:
                proc = subprocess.run(
                    ["ollama", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                ollama_version = (proc.stdout or proc.stderr).strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                ollama_version = f"error: {exc}"
        report["ollama_version"] = ollama_version
        return ToolResult(success=True, output=report, message="environment snapshot")
