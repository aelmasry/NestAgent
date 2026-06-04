"""Tool contract — reusable capabilities executed by the Harness."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: Any
    message: str = ""


class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    def validate_input(self, **kwargs: Any) -> list[str]:
        return []

    def to_spec(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description}
