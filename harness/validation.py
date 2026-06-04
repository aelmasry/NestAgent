"""Environment and tool validation — Harness-owned, not LLM-owned."""

from __future__ import annotations

import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from config.settings import Settings
from tools.base import Tool


@dataclass
class ReadinessReport:
    ready: bool
    checks: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ready": self.ready, "checks": self.checks, "messages": self.messages}


def check_environment(settings: Settings) -> ReadinessReport:
    report = ReadinessReport(ready=True)
    py_ok = bool(shutil.which("python3") or shutil.which("python"))
    report.checks["python"] = py_ok
    if not py_ok:
        report.ready = False
        report.messages.append("Python غير متوفر في PATH")

    pip_ok = bool(shutil.which("pip3") or shutil.which("pip"))
    report.checks["pip"] = pip_ok
    if not pip_ok:
        report.ready = False
        report.messages.append("pip غير متوفر في PATH")

    ollama_ok = False
    try:
        url = f"{settings.ollama.base_url.rstrip('/')}/api/version"
        with urllib.request.urlopen(url, timeout=5) as resp:
            ollama_ok = resp.status == 200
    except (urllib.error.URLError, TimeoutError):
        ollama_ok = False
    report.checks["ollama_http"] = ollama_ok
    if not ollama_ok:
        report.ready = False
        report.messages.append("Ollama API غير متاح على المنفذ 11434")

    return report


@dataclass
class ToolValidationResult:
    approved: bool
    reasons: list[str] = field(default_factory=list)


def validate_tool_spec(spec: dict[str, Any], registry_names: set[str]) -> ToolValidationResult:
    reasons: list[str] = []
    name = spec.get("name")
    if not name or not isinstance(name, str):
        reasons.append("اسم الأداة مطلوب")
    elif name in registry_names:
        reasons.append("أداة مكررة في السجل")
    if not spec.get("description"):
        reasons.append("وصف الأداة مطلوب")
    if "inputs" not in spec or "outputs" not in spec:
        reasons.append("يجب تحديد inputs و outputs")
    return ToolValidationResult(approved=len(reasons) == 0, reasons=reasons)


def validate_tool_instance(tool: Tool) -> ToolValidationResult:
    reasons: list[str] = []
    if not tool.name:
        reasons.append("name فارغ")
    if not tool.description:
        reasons.append("description فارغ")
    return ToolValidationResult(approved=len(reasons) == 0, reasons=reasons)
