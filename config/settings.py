"""Central configuration for NestAgent (no framework dependencies)."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class OllamaSettings:
    base_url: str = "http://127.0.0.1:11434"
    planner_model: str = "qwen2.5-coder:7b"
    timeout_seconds: float = 120.0


@dataclass(frozen=True)
class HarnessSettings:
    max_retries: int = 2
    github_search_limit: int = 5


@dataclass(frozen=True)
class Settings:
    ollama: OllamaSettings
    harness: HarnessSettings
    project_root: str


def load_settings() -> Settings:
    root = os.environ.get("NESTAGENT_ROOT", os.getcwd())
    return Settings(
        ollama=OllamaSettings(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            planner_model=os.environ.get(
                "NESTAGENT_PLANNER_MODEL", "qwen2.5-coder:7b"
            ),
            timeout_seconds=float(os.environ.get("OLLAMA_TIMEOUT", "120")),
        ),
        harness=HarnessSettings(
            max_retries=int(os.environ.get("NESTAGENT_MAX_RETRIES", "2")),
            github_search_limit=int(os.environ.get("NESTAGENT_GITHUB_LIMIT", "5")),
        ),
        project_root=root,
    )
