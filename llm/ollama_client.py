"""Ollama HTTP client — used only for planning (not execution)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from config.settings import OllamaSettings


@dataclass
class PlannerResponse:
    raw: str
    parsed: dict[str, Any] | None


class OllamaClient:
    def __init__(self, settings: OllamaSettings) -> None:
        self._settings = settings

    def health(self) -> dict[str, Any]:
        return self._get("/api/version")

    def list_models(self) -> list[str]:
        data = self._get("/api/tags")
        return [m["name"] for m in data.get("models", [])]

    def plan(self, system_prompt: str, user_prompt: str) -> PlannerResponse:
        payload = {
            "model": self._settings.planner_model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
        }
        data = self._post("/api/chat", payload)
        content = (data.get("message") or {}).get("content", "")
        parsed = None
        try:
            parsed = json.loads(content) if content.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return PlannerResponse(raw=content, parsed=parsed)

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}{path}"
        req = urllib.request.Request(url, method="GET")
        return self._read(req)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._settings.base_url.rstrip('/')}{path}"
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._read(req)

    def _read(self, req: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(
                req, timeout=self._settings.timeout_seconds
            ) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Ollama unreachable: {exc}") from exc
