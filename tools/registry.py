"""Tool registry — lookup before creating new tools."""

from __future__ import annotations

from typing import Any

import os

from tools.base import Tool, ToolResult
from tools.apartment_mock import ApartmentSearchMockTool
from tools.builtin import EchoTool, EnvironmentCheckTool
from tools.filesystem import ListDirTool, ReadFileTool


class ToolRegistry:
    def __init__(self, project_root: str | None = None) -> None:
        root = project_root or os.environ.get("NESTAGENT_ROOT", os.getcwd())
        self._tools: dict[str, Tool] = {}
        for tool in (
            EchoTool(),
            EnvironmentCheckTool(),
            ListDirTool(root),
            ReadFileTool(root),
            ApartmentSearchMockTool(),
        ):
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_specs(self) -> list[dict[str, Any]]:
        return [t.to_spec() for t in self._tools.values()]

    def names(self) -> set[str]:
        return set(self._tools.keys())

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, output=None, message=f"tool not found: {name}")
        errors = tool.validate_input(**kwargs)
        if errors:
            return ToolResult(success=False, output=None, message="; ".join(errors))
        return tool.run(**kwargs)
