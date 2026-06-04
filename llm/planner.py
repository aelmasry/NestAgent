"""LLM planner — produces structured plans; Harness decides and executes."""

from __future__ import annotations

import json
from typing import Any

from llm.ollama_client import OllamaClient, PlannerResponse

PLANNER_SYSTEM = """You are the PLANNER for NestAgent. You do NOT execute tools.
Return ONLY valid JSON with this shape:
{
  "goal": "short description",
  "steps": [
    {"action": "use_tool|search_github|propose_tool", "tool": "name or null", "input": {}, "reason": "why"}
  ],
  "acceptance": "how to verify success"
}
"""


class Planner:
    def __init__(self, client: OllamaClient) -> None:
        self._client = client

    def create_plan(self, user_request: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = json.dumps(context or {}, ensure_ascii=False)
        user_prompt = f"User request:\n{user_request}\n\nContext:\n{ctx}"
        response: PlannerResponse = self._client.plan(PLANNER_SYSTEM, user_prompt)
        if response.parsed and isinstance(response.parsed, dict):
            return response.parsed
        return {
            "goal": user_request,
            "steps": [{"action": "propose_tool", "tool": None, "input": {}, "reason": "planner JSON parse failed"}],
            "acceptance": "manual review",
            "_raw": response.raw,
        }

    def propose_tool(self, need: str) -> dict[str, Any]:
        user_prompt = f"""Design a reusable tool for: {need}
Return ONLY JSON:
{{"name": "snake_case", "description": "...", "inputs": {{}}, "outputs": {{}}, "safety_notes": "..."}}"""
        response = self._client.plan(PLANNER_SYSTEM, user_prompt)
        if response.parsed:
            return response.parsed
        return {"name": "unknown", "description": need, "_raw": response.raw}
