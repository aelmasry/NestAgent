#!/usr/bin/env python3
"""Local NestAgent web console using only Python stdlib."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import socket
import sys
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18080
NOT_FOUND = "not found"
METRO_THRESHOLD_METERS = 800
STREAM_DELAY_SECONDS = 0.08


def _ensure_project_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("NESTAGENT_ROOT", str(root))
    return root


PROJECT_ROOT = _ensure_project_root()
STATIC_ROOT = Path(__file__).resolve().parent / "static"


def _port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def choose_port(host: str, requested: int) -> int:
    """Return requested port if free, or the next free high port."""
    if requested == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    if _port_available(host, requested):
        return requested

    for port in range(max(requested + 1, 18081), 65000):
        if _port_available(host, port):
            return port
    raise RuntimeError("no available TCP port found")


def event_payload(
    event_type: str,
    status: str,
    details: str,
    *,
    duration_ms: float = 0,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "status": status,
        "details": details,
        "data": data or {},
    }


def timed_call(fn: Any, *args: Any) -> tuple[Any, float]:
    started = time.perf_counter()
    result = fn(*args)
    return result, round((time.perf_counter() - started) * 1000, 2)


def stream_dashboard_events(
    request: str, registry: Any
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = [
        event_payload(
            "request_received",
            "complete",
            "Received user request.",
            data={"request": request},
        )
    ]

    events.append(
        event_payload("planning_started", "running", "Starting goal analysis.")
    )

    constraints, constraints_ms = timed_call(dashboard_constraints)
    goal_parser, parser_ms = timed_call(dashboard_goal_parser, constraints)
    events.append(
        event_payload(
            "goal_parsed",
            "complete",
            "Parsed intent, constraints, missing fields, and confidence.",
            duration_ms=round(constraints_ms + parser_ms, 2),
            data=goal_parser,
        )
    )

    capability_manager, capability_ms = timed_call(
        dashboard_capability_manager, registry
    )
    events.append(
        event_payload(
            "planning_finished",
            "complete",
            "Finished capability analysis for the current goal.",
            duration_ms=capability_ms,
            data=capability_manager,
        )
    )

    tool_inputs = {
        "query": request,
        "max_price": constraints["max_price"],
        "currency": constraints["currency"],
        "near_metro": constraints["near_metro"],
    }
    tool_registry = {
        "selected_tool": "apartment_search_mock",
        "tool_status": "available" if registry.has("apartment_search_mock") else "missing",
        "tool_inputs": tool_inputs,
    }
    events.append(
        event_payload(
            "tool_selected",
            tool_registry["tool_status"],
            "Selected a registered tool for the required capability.",
            data=tool_registry,
        )
    )

    events.append(
        event_payload(
            "tool_started",
            "running",
            "Starting tool execution.",
            data={"tool": tool_registry["selected_tool"], "input": tool_inputs},
        )
    )
    tool_execution, tool_ms = timed_call(execute_dashboard_tool, request, registry, constraints)
    tool_registry, tool_execution = tool_execution
    tool_execution["execution_duration_ms"] = tool_ms
    events.append(
        event_payload(
            "tool_finished",
            tool_execution["execution_status"],
            "Tool execution finished.",
            duration_ms=tool_ms,
            data=tool_execution,
        )
    )

    evidence, evidence_ms = timed_call(normalize_dashboard_evidence, tool_execution)
    events.append(
        event_payload(
            "evidence_collected",
            "complete",
            "Normalized tool output into evidence records.",
            duration_ms=evidence_ms,
            data={"count": len(evidence), "evidence": evidence},
        )
    )

    events.append(
        event_payload(
            "validation_started",
            "running",
            "Starting goal validation against collected evidence.",
        )
    )
    validator_result, validation_ms = timed_call(validate_dashboard_goal, evidence, constraints)
    goal_validator, validation_decisions = validator_result
    events.append(
        event_payload(
            "validation_finished",
            goal_validator["goal_status"],
            "Goal validation finished.",
            duration_ms=validation_ms,
            data=goal_validator,
        )
    )

    final_answer, response_ms = timed_call(
        compose_dashboard_answer,
        goal_validator["goal_status"],
        goal_validator["valid_results"],
        goal_validator["rejected_results"],
        goal_validator["unknown_results"],
    )
    events.append(
        event_payload(
            "response_generated",
            "complete",
            "Generated final response for the user.",
            duration_ms=response_ms,
            data={"final_answer": final_answer},
        )
    )

    timeline = dashboard_timeline(
        tool_registry, tool_execution, goal_validator["goal_status"]
    )
    total_runtime_ms = round(sum(event["duration_ms"] for event in events), 2)
    planner_output = dashboard_planner_output(
        tool_registry["selected_tool"], tool_registry["tool_inputs"]
    )
    payload = {
        "user_request": request,
        "user_view": {
            "goal": request,
            "current_status": goal_validator["goal_status"],
            "progress": f"{len(timeline)}/{len(timeline)} steps complete",
            "elapsed_time_ms": total_runtime_ms,
        },
        "agent_activity_feed": events,
        "goal_parser": goal_parser,
        "capability_manager": capability_manager,
        "tool_registry": tool_registry,
        "tool_execution": tool_execution,
        "evidence_store": {"evidence": evidence},
        "goal_validator": goal_validator,
        "response_composer": {"final_answer": final_answer},
        "workflow_timeline": timeline,
        "timeline_view": {
            "steps": timeline,
            "total_runtime_ms": total_runtime_ms,
            "current_step": "Response",
        },
        "developer_view": {
            "planner_output": planner_output,
            "selected_capabilities": capability_manager["required_capabilities"],
            "evidence_generated": evidence,
            "validation_decisions": validation_decisions,
        },
    }
    return events, payload


def dashboard_constraints() -> dict[str, Any]:
    return {
        "property_type": "apartment",
        "max_price": 4000,
        "currency": "AED",
        "near_metro": True,
        "metro_threshold_meters": METRO_THRESHOLD_METERS,
    }


def dashboard_goal_parser(constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": "property_search",
        "constraints": constraints,
        "missing_fields": ["city", "rent_period"],
        "confidence": 0.88,
    }


def dashboard_capability_manager(registry: Any) -> dict[str, list[str]]:
    required_capabilities = ["property_search"]
    available_capabilities = (
        ["property_search"] if registry.has("apartment_search_mock") else []
    )
    missing_capabilities = [
        cap for cap in required_capabilities if cap not in available_capabilities
    ]
    return {
        "required_capabilities": required_capabilities,
        "available_capabilities": available_capabilities,
        "missing_capabilities": missing_capabilities,
    }


def execute_dashboard_tool(
    request: str, registry: Any, constraints: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    tool_inputs = {
        "query": request,
        "max_price": constraints["max_price"],
        "currency": constraints["currency"],
        "near_metro": constraints["near_metro"],
    }
    selected_tool = "apartment_search_mock"
    tool_registry = {
        "selected_tool": selected_tool,
        "tool_status": "available" if registry.has(selected_tool) else "missing",
        "tool_inputs": tool_inputs,
    }

    started = time.perf_counter()
    tool_result = registry.execute(selected_tool, **tool_inputs)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    tool_execution = {
        "execution_status": "success" if tool_result.success else "failed",
        "execution_duration_ms": duration_ms,
        "raw_tool_result": tool_result.output,
    }
    return tool_registry, tool_execution


def normalize_dashboard_evidence(tool_execution: dict[str, Any]) -> list[dict[str, Any]]:
    raw_result = tool_execution["raw_tool_result"]
    apartments = raw_result.get("apartments", [])
    evidence = []
    for apartment in apartments:
        metro_distance = apartment.get("metro_distance")
        evidence.append(
            {
                "id": apartment.get("id"),
                "title": apartment.get("title"),
                "price": apartment.get("price"),
                "currency": apartment.get("currency"),
                "metro_distance": metro_distance,
                "source": apartment.get("source"),
                "confidence": 0.95 if metro_distance is not None else 0.62,
            }
        )
    return evidence


def evidence_reasons(item: dict[str, Any], constraints: dict[str, Any]) -> list[str]:
    reasons = []
    if item["price"] > constraints["max_price"]:
        reasons.append("price_above_budget")
    if item["metro_distance"] is None:
        reasons.append("metro_distance_missing")
    elif item["metro_distance"] > constraints["metro_threshold_meters"]:
        reasons.append("too_far_from_metro")
    return reasons


def validate_dashboard_goal(
    evidence: list[dict[str, Any]], constraints: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    valid_results = []
    rejected_results = []
    unknown_results = []
    validation_decisions = []

    for item in evidence:
        reasons = evidence_reasons(item, constraints)
        decision = {"id": item["id"], "title": item["title"], "reasons": reasons}
        if "metro_distance_missing" in reasons:
            unknown_results.append({**item, "reasons": reasons})
            decision["status"] = "unknown"
        elif reasons:
            rejected_results.append({**item, "reasons": reasons})
            decision["status"] = "rejected"
        else:
            valid_results.append(item)
            decision["status"] = "valid"
        validation_decisions.append(decision)

    goal_status = dashboard_goal_status(
        valid_results, rejected_results, unknown_results
    )
    validation_reasons = dashboard_validation_reasons(
        rejected_results, unknown_results
    )
    return {
        "goal_status": goal_status,
        "validation_reasons": validation_reasons,
        "valid_results": valid_results,
        "rejected_results": rejected_results,
        "unknown_results": unknown_results,
    }, validation_decisions


def dashboard_goal_status(
    valid_results: list[dict[str, Any]],
    rejected_results: list[dict[str, Any]],
    unknown_results: list[dict[str, Any]],
) -> str:
    if valid_results and (rejected_results or unknown_results):
        return "partially_achieved"
    if valid_results:
        return "achieved"
    if unknown_results and not rejected_results:
        return "unknown"
    return "not_achieved"


def dashboard_validation_reasons(
    rejected_results: list[dict[str, Any]], unknown_results: list[dict[str, Any]]
) -> list[str]:
    reasons = []
    for item in rejected_results + unknown_results:
        reasons.extend(f"{item['title']}: {reason}" for reason in item["reasons"])
    return reasons


def dashboard_timeline(
    tool_registry: dict[str, Any], tool_execution: dict[str, Any], goal_status: str
) -> list[dict[str, Any]]:
    return [
        {"name": "Goal Parsing", "status": "complete", "duration_ms": 4},
        {"name": "Capability Analysis", "status": "complete", "duration_ms": 3},
        {"name": "Tool Selection", "status": tool_registry["tool_status"], "duration_ms": 2},
        {
            "name": "Tool Execution",
            "status": tool_execution["execution_status"],
            "duration_ms": tool_execution["execution_duration_ms"],
        },
        {"name": "Evidence Collection", "status": "complete", "duration_ms": 3},
        {"name": "Validation", "status": goal_status, "duration_ms": 5},
        {"name": "Response", "status": "complete", "duration_ms": 2},
    ]


def dashboard_planner_output(
    selected_tool: str, tool_inputs: dict[str, Any]
) -> dict[str, Any]:
    return {
        "goal": "Find apartment under 4000 AED near metro",
        "steps": [
            {
                "action": "use_tool",
                "tool": selected_tool,
                "capability": "property_search",
                "input": tool_inputs,
            }
        ],
        "acceptance": "Return valid, rejected, and unknown apartment results with reasons.",
    }


def build_dashboard_payload(request: str, registry: Any) -> dict[str, Any]:
    """Build a visual workflow payload for the MVP mock apartment flow."""
    constraints = dashboard_constraints()
    goal_parser = dashboard_goal_parser(constraints)
    capability_manager = dashboard_capability_manager(registry)
    tool_registry, tool_execution = execute_dashboard_tool(
        request, registry, constraints
    )
    evidence = normalize_dashboard_evidence(tool_execution)
    goal_validator, validation_decisions = validate_dashboard_goal(
        evidence, constraints
    )
    final_answer = compose_dashboard_answer(
        goal_validator["goal_status"],
        goal_validator["valid_results"],
        goal_validator["rejected_results"],
        goal_validator["unknown_results"],
    )
    timeline = dashboard_timeline(
        tool_registry, tool_execution, goal_validator["goal_status"]
    )
    total_runtime_ms = round(sum(step["duration_ms"] for step in timeline), 2)
    planner_output = dashboard_planner_output(
        tool_registry["selected_tool"], tool_registry["tool_inputs"]
    )

    return {
        "user_request": request,
        "user_view": {
            "goal": request,
            "current_status": goal_validator["goal_status"],
            "progress": f"{len(timeline)}/{len(timeline)} steps complete",
            "elapsed_time_ms": total_runtime_ms,
        },
        "agent_activity_feed": dashboard_activity_feed(
            request,
            tool_registry,
            tool_execution,
            goal_validator,
            timeline,
        ),
        "goal_parser": goal_parser,
        "capability_manager": capability_manager,
        "tool_registry": tool_registry,
        "tool_execution": tool_execution,
        "evidence_store": {"evidence": evidence},
        "goal_validator": goal_validator,
        "response_composer": {"final_answer": final_answer},
        "workflow_timeline": timeline,
        "timeline_view": {
            "steps": timeline,
            "total_runtime_ms": total_runtime_ms,
            "current_step": "Response",
        },
        "developer_view": {
            "planner_output": planner_output,
            "selected_capabilities": capability_manager["required_capabilities"],
            "evidence_generated": evidence,
            "validation_decisions": validation_decisions,
        },
    }


def dashboard_activity_feed(
    request: str,
    tool_registry: dict[str, Any],
    tool_execution: dict[str, Any],
    goal_validator: dict[str, Any],
    timeline: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "type": "thinking",
            "title": "Received request",
            "detail": request,
            "status": "complete",
            "duration_ms": timeline[0]["duration_ms"],
        },
        {
            "type": "planning",
            "title": "Parsed goal and constraints",
            "detail": "Converted the prompt into a structured goal contract.",
            "status": "complete",
            "duration_ms": timeline[0]["duration_ms"],
        },
        {
            "type": "planning",
            "title": "Analyzed required capabilities",
            "detail": "Checked which capabilities are required for this goal.",
            "status": "complete",
            "duration_ms": timeline[1]["duration_ms"],
        },
        {
            "type": "tool_selection",
            "title": "Selected tool",
            "detail": tool_registry["selected_tool"],
            "status": tool_registry["tool_status"],
            "duration_ms": timeline[2]["duration_ms"],
        },
        {
            "type": "tool_execution",
            "title": "Executed selected tool",
            "detail": f"Execution status: {tool_execution['execution_status']}",
            "status": tool_execution["execution_status"],
            "duration_ms": tool_execution["execution_duration_ms"],
        },
        {
            "type": "validation",
            "title": "Validated evidence against goal",
            "detail": f"Goal status: {goal_validator['goal_status']}",
            "status": goal_validator["goal_status"],
            "duration_ms": timeline[5]["duration_ms"],
        },
        {
            "type": "response",
            "title": "Composed final response",
            "detail": "Prepared the user-facing answer from validated evidence.",
            "status": "complete",
            "duration_ms": timeline[6]["duration_ms"],
        },
    ]


def compose_dashboard_answer(
    goal_status: str,
    valid_results: list[dict[str, Any]],
    rejected_results: list[dict[str, Any]],
    unknown_results: list[dict[str, Any]],
) -> str:
    if goal_status == "partially_achieved":
        return (
            f"Goal partially achieved. Found {len(valid_results)} matching apartment(s) "
            f"under 4000 AED near metro. {len(rejected_results)} rejected and "
            f"{len(unknown_results)} require more evidence."
        )
    if goal_status == "achieved":
        return f"Goal achieved. Found {len(valid_results)} matching apartment(s)."
    if goal_status == "unknown":
        return "Goal status unknown. Listings exist, but required metro evidence is missing."
    return "Goal not achieved. No apartment satisfied the requested constraints."


class NestAgentHandler(BaseHTTPRequestHandler):
    server_version = "NestAgentWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path.startswith("/static/"):
            self._serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/ready":
            self._send_json(self._harness().readiness())
            return
        if parsed.path == "/api/tools":
            self._send_json(self._harness().registry.list_specs())
            return
        if parsed.path == "/api/models":
            from llm.ollama_client import OllamaClient

            try:
                client = OllamaClient(self._settings().ollama)
                self._send_json({"models": client.list_models()})
            except Exception as exc:  # noqa: BLE001 - API boundary returns errors as JSON.
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return
        if parsed.path == "/api/dashboard/stream":
            self._stream_dashboard(parsed)
            return
        self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/run", "/api/dashboard/run"}:
            self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)
            return

        try:
            payload = self._read_json()
            request = str(payload.get("request", "")).strip()
            use_planner = bool(payload.get("use_planner", True))
            if not request:
                self._send_json({"error": "request is required"}, HTTPStatus.BAD_REQUEST)
                return
            if parsed.path == "/api/dashboard/run":
                self._send_json(build_dashboard_payload(request, self._harness().registry))
                return
            result = self._harness().run(request, use_planner=use_planner)
            self._send_json(result)
        except json.JSONDecodeError:
            self._send_json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - keep UI usable during harness errors.
            self._send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {fmt % args}")

    def _stream_dashboard(self, parsed: Any) -> None:
        params = parse_qs(parsed.query)
        request = str((params.get("request") or [""])[0]).strip()
        if not request:
            self._send_json({"error": "request is required"}, HTTPStatus.BAD_REQUEST)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        events, final_payload = stream_dashboard_events(request, self._harness().registry)
        for event in events:
            self._send_sse("activity", event)
            time.sleep(STREAM_DELAY_SECONDS)
        self._send_sse("final", final_payload)

    def _send_sse(self, event_name: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False)
        self.wfile.write(f"event: {event_name}\n".encode("utf-8"))
        self.wfile.write(f"data: {body}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _settings(self):
        from config.settings import load_settings

        return load_settings()

    def _harness(self):
        from harness.engine import Harness

        return Harness(self._settings())

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8")) if raw else {}

    def _send_json(
        self, payload: Any, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, rel_path: str) -> None:
        target = (STATIC_ROOT / rel_path).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self._send_json({"error": "invalid path"}, HTTPStatus.BAD_REQUEST)
            return
        if not target.exists() or not target.is_file():
            self._send_json({"error": NOT_FOUND}, HTTPStatus.NOT_FOUND)
            return

        content = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="NestAgent web console")
    parser.add_argument("--host", default=os.environ.get("NESTAGENT_WEB_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("NESTAGENT_WEB_PORT", str(DEFAULT_PORT))),
        help="Use 0 for a fully dynamic port.",
    )
    args = parser.parse_args()

    port = choose_port(args.host, args.port)
    if port != args.port and args.port != 0:
        print(f"Port {args.port} is busy; using {port} instead.")

    server = ThreadingHTTPServer((args.host, port), NestAgentHandler)
    print(f"NestAgent web console: http://{args.host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping NestAgent web console.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
