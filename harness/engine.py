"""Harness — decision and execution engine (LLM plans only)."""

from __future__ import annotations

from typing import Any

from config.settings import Settings, load_settings
from discovery.github import GitHubDiscovery
from harness.validation import check_environment, validate_tool_spec
from harness.workflow import StepPhase, WorkflowRun
from llm.ollama_client import OllamaClient
from llm.planner import Planner
from tools.registry import ToolRegistry


class Harness:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.registry = ToolRegistry()
        self.client = OllamaClient(self.settings.ollama)
        self.planner = Planner(self.client)
        self.discovery = GitHubDiscovery(limit=self.settings.harness.github_search_limit)

    def readiness(self) -> dict[str, Any]:
        return check_environment(self.settings).to_dict()

    def run(self, user_request: str, *, use_planner: bool = True) -> dict[str, Any]:
        run = WorkflowRun(request=user_request)

        # 1. Analyze + 2. Environment
        readiness = check_environment(self.settings)
        run.add(
            StepPhase.PLAN,
            "environment",
            "فحص جاهزية البيئة",
            ok=readiness.ready,
            report=readiness.to_dict(),
        )
        if not readiness.ready:
            run.add(StepPhase.REVIEW, "blocked", "توقف — البيئة غير جاهزة", ok=False)
            return run.to_dict()

        run.add(StepPhase.REVIEW, "environment", "البيئة جاهزة", ok=True)

        context: dict[str, Any] = {"tools": self.registry.list_specs()}

        # 3. LLM planning
        plan: dict[str, Any]
        if use_planner:
            try:
                plan = self.planner.create_plan(user_request, context)
                run.add(StepPhase.PLAN, "llm_plan", "خطة من المخطط", ok=True, plan=plan)
            except ConnectionError as exc:
                plan = {"goal": user_request, "steps": [], "acceptance": "n/a"}
                run.add(StepPhase.PLAN, "llm_plan", str(exc), ok=False)
                use_planner = False
        else:
            plan = {"goal": user_request, "steps": [], "acceptance": "n/a"}

        run.add(StepPhase.REVIEW, "plan", "مراجعة الخطة", ok=bool(plan.get("steps")), plan=plan)

        # 4–10. Execute steps from plan (or fallback)
        steps = plan.get("steps") or [
            {"action": "use_tool", "tool": "environment_check", "input": {}, "reason": "default"}
        ]
        results: list[dict[str, Any]] = []

        for idx, step in enumerate(steps):
            action = step.get("action", "use_tool")
            tool_name = step.get("tool")
            tool_input = step.get("input") or {}

            if action == "search_github":
                query = step.get("reason") or user_request
                hits = self.discovery.search_repositories(query)
                ctx = self.discovery.to_context(hits)
                run.add(
                    StepPhase.EXECUTE,
                    f"github_{idx}",
                    f"بحث GitHub: {query}",
                    ok=len(hits) > 0,
                    hits=ctx,
                )
                results.append({"action": action, "hits": ctx})
                continue

            if action == "propose_tool":
                need = step.get("reason") or user_request
                github_hits = self.discovery.search_repositories(need)
                run.add(
                    StepPhase.EXECUTE,
                    f"github_before_propose_{idx}",
                    "بحث مفتوح المصدر قبل اقتراح أداة",
                    ok=True,
                    hits=self.discovery.to_context(github_hits),
                )
                spec = self.planner.propose_tool(need)
                validation = validate_tool_spec(spec, self.registry.names())
                run.add(
                    StepPhase.REVIEW,
                    f"tool_validation_{idx}",
                    "تحقق من اقتراح الأداة",
                    ok=validation.approved,
                    spec=spec,
                    reasons=validation.reasons,
                )
                results.append({"action": action, "spec": spec, "approved": validation.approved})
                continue

            # use_tool (default)
            if not tool_name:
                tool_name = "echo"
                tool_input = {"message": user_request}

            if not self.registry.has(tool_name):
                hits = self.discovery.search_repositories(tool_name)
                run.add(
                    StepPhase.EXECUTE,
                    f"missing_tool_{idx}",
                    f"الأداة غير موجودة — بحث GitHub: {tool_name}",
                    ok=bool(hits),
                    hits=self.discovery.to_context(hits),
                )
                results.append(
                    {
                        "action": "use_tool",
                        "tool": tool_name,
                        "success": False,
                        "message": "tool not in registry",
                        "github": self.discovery.to_context(hits),
                    }
                )
                continue

            attempt = 0
            last = None
            while attempt <= self.settings.harness.max_retries:
                last = self.registry.execute(tool_name, **tool_input)
                if last.success:
                    break
                attempt += 1

            ok = bool(last and last.success)
            run.add(
                StepPhase.EXECUTE,
                f"tool_{idx}",
                f"تنفيذ {tool_name}",
                ok=ok,
                output=last.output if last else None,
                message=last.message if last else "",
            )
            run.add(
                StepPhase.VALIDATE,
                f"accept_{idx}",
                plan.get("acceptance", "تحقق من النتيجة"),
                ok=ok,
            )
            results.append(
                {
                    "action": "use_tool",
                    "tool": tool_name,
                    "success": ok,
                    "output": last.output if last else None,
                }
            )

        run.add(StepPhase.REVIEW, "complete", "انتهاء التشغيل", ok=True, results=results)
        return run.to_dict()
