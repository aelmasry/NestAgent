#!/usr/bin/env python3
"""NestAgent CLI entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys


def _ensure_project_root() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault("NESTAGENT_ROOT", root)


def main() -> int:
    _ensure_project_root()
    from config.settings import load_settings
    from harness.engine import Harness
    from llm.ollama_client import OllamaClient

    parser = argparse.ArgumentParser(description="NestAgent Harness")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ready", help="Check environment readiness")

    sub.add_parser("tools", help="List registered Harness tools")
    sub.add_parser("models", help="List Ollama models")
    web_p = sub.add_parser("web", help="Start local web console")
    web_p.add_argument("--host", default=None, help="Host to bind, default 127.0.0.1")
    web_p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind. Use 0 for a fully dynamic port.",
    )
    run_p = sub.add_parser("run", help="Run Harness on a request")
    run_p.add_argument("request", help="User request text")
    run_p.add_argument(
        "--no-planner",
        action="store_true",
        help="Skip LLM planning (tools only)",
    )

    args = parser.parse_args()
    settings = load_settings()
    harness = Harness(settings)

    if args.command == "ready":
        print(json.dumps(harness.readiness(), ensure_ascii=False, indent=2))
        return 0 if harness.readiness().get("ready") else 1

    if args.command == "tools":
        print(json.dumps(harness.registry.list_specs(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "models":
        client = OllamaClient(settings.ollama)
        for name in client.list_models():
            print(name)
        return 0

    if args.command == "web":
        from web.server import main as web_main

        argv = ["web"]
        if args.host is not None:
            argv.extend(["--host", args.host])
        if args.port is not None:
            argv.extend(["--port", str(args.port)])
        old_argv = sys.argv
        try:
            sys.argv = argv
            return web_main()
        finally:
            sys.argv = old_argv

    if args.command == "run":
        result = harness.run(args.request, use_planner=not args.no_planner)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
