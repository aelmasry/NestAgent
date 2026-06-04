"""Restrict filesystem tools to paths under the project root."""

from __future__ import annotations

from pathlib import Path


class PathGuardError(ValueError):
    pass


def resolve_under_root(root: str | Path, user_path: str) -> Path:
    base = Path(root).resolve()
    if not user_path or user_path.strip() == "":
        target = base
    else:
        candidate = Path(user_path)
        target = (base / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()

    try:
        target.relative_to(base)
    except ValueError as exc:
        raise PathGuardError(f"path outside project root: {user_path}") from exc

    return target
