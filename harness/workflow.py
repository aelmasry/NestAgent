"""Mandatory workflow steps — plan, review, execute."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepPhase(str, Enum):
    PLAN = "plan"
    REVIEW = "review"
    EXECUTE = "execute"
    VALIDATE = "validate"


@dataclass
class WorkflowStep:
    phase: StepPhase
    name: str
    detail: str
    ok: bool = True
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRun:
    request: str
    steps: list[WorkflowStep] = field(default_factory=list)

    def add(self, phase: StepPhase, name: str, detail: str, ok: bool = True, **data: Any) -> None:
        self.steps.append(
            WorkflowStep(phase=phase, name=name, detail=detail, ok=ok, data=dict(data))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "steps": [
                {
                    "phase": s.phase.value,
                    "name": s.name,
                    "detail": s.detail,
                    "ok": s.ok,
                    "data": s.data,
                }
                for s in self.steps
            ],
        }
