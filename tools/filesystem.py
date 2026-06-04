"""Filesystem tools — list and read files within the project root only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.base import Tool, ToolResult
from tools.path_guard import PathGuardError, resolve_under_root

DEFAULT_MAX_BYTES = 64_000


class ListDirTool(Tool):
    name = "list_dir"
    description = "List files and directories under a path inside the project."

    def __init__(self, project_root: str) -> None:
        self._root = project_root

    def validate_input(self, **kwargs: Any) -> list[str]:
        errors: list[str] = []
        if kwargs.get("max_depth", 2) > 4:
            errors.append("max_depth must be <= 4")
        return errors

    def run(self, **kwargs: Any) -> ToolResult:
        rel_path = kwargs.get("path", ".")
        max_depth = int(kwargs.get("max_depth", 2))
        try:
            root = resolve_under_root(self._root, rel_path)
        except PathGuardError as exc:
            return ToolResult(success=False, output=None, message=str(exc))

        if not root.exists():
            return ToolResult(success=False, output=None, message=f"not found: {rel_path}")
        if not root.is_dir():
            return ToolResult(success=False, output=None, message=f"not a directory: {rel_path}")

        entries: list[dict[str, Any]] = []
        base = Path(self._root).resolve()
        for path in sorted(root.rglob("*")):
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                continue
            rel = path.relative_to(base).as_posix()
            entries.append(
                {
                    "path": rel,
                    "type": "dir" if path.is_dir() else "file",
                    "size": path.stat().st_size if path.is_file() else None,
                }
            )

        return ToolResult(
            success=True,
            output={"path": rel_path, "count": len(entries), "entries": entries},
            message="ok",
        )


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read a text file inside the project (size-capped)."

    def __init__(self, project_root: str) -> None:
        self._root = project_root

    def validate_input(self, **kwargs: Any) -> list[str]:
        errors: list[str] = []
        if not kwargs.get("path"):
            errors.append("path is required")
        max_bytes = int(kwargs.get("max_bytes", DEFAULT_MAX_BYTES))
        if max_bytes < 1 or max_bytes > 512_000:
            errors.append("max_bytes must be between 1 and 512000")
        return errors

    def run(self, **kwargs: Any) -> ToolResult:
        rel_path = kwargs["path"]
        max_bytes = int(kwargs.get("max_bytes", DEFAULT_MAX_BYTES))
        try:
            target = resolve_under_root(self._root, rel_path)
        except PathGuardError as exc:
            return ToolResult(success=False, output=None, message=str(exc))

        if not target.exists():
            return ToolResult(success=False, output=None, message=f"not found: {rel_path}")
        if not target.is_file():
            return ToolResult(success=False, output=None, message=f"not a file: {rel_path}")

        size = target.stat().st_size
        if size > max_bytes:
            return ToolResult(
                success=False,
                output={"size": size, "max_bytes": max_bytes},
                message=f"file too large ({size} bytes); increase max_bytes or read partially",
            )

        content = target.read_text(encoding="utf-8", errors="replace")
        return ToolResult(
            success=True,
            output={"path": rel_path, "size": size, "content": content},
            message="ok",
        )
