# NestAgent Project Summary

## What We Finished

NestAgent now has a working pure-Python Harness foundation. The LLM is used only as a planner through Ollama, while the Harness owns validation, decision flow, tool lookup, execution, retries, and result review.

Completed pieces:

- Project scaffold with `config/`, `harness/`, `llm/`, `tools/`, `discovery/`, `web/`, and `tests/`.
- Ollama HTTP client and JSON-only planner.
- Harness workflow with explicit plan, review, execute, and validate phases.
- Environment readiness checks for Python, pip, and Ollama HTTP.
- Tool registry with reusable built-in tools.
- Filesystem tools constrained to the project root:
  - `list_dir`
  - `read_file`
  - `path_guard`
- GitHub repository discovery module for checking open source before proposing a new tool.
- Local browser console at `python main.py web`.
- Dynamic web port handling:
  - default `18080`
  - automatic fallback if busy
  - `--port 0` for fully dynamic port selection
- Tests for registry, validation, filesystem safety, and web port selection.

## Current Commands

```bash
source .venv/bin/activate

python main.py ready
python main.py tools
python main.py models
python main.py run "check environment" --no-planner
python main.py run "check environment"
python main.py web
python main.py web --port 0
pytest
```

## Architecture Rules

- LLM = planner only.
- Harness = decision and execution engine.
- Tools = reusable capabilities.
- Check the tool registry before creating a new tool.
- Search GitHub/open-source before designing a new tool.
- Validate environment readiness before execution.
- Keep the project pure Python and stdlib-first.
- No LangChain, LangGraph, CrewAI, or agent frameworks.

## Current Tool Registry

- `echo`: smoke-test tool.
- `environment_check`: reports Python, pip, git, Ollama, and platform details.
- `list_dir`: lists project files under a safe root.
- `read_file`: reads text files under a safe root with size limits.

## Web Console

The local web console is intentionally simple and stdlib-only.

Endpoints:

- `GET /api/ready`
- `GET /api/tools`
- `GET /api/models`
- `POST /api/run`

The UI supports:

- entering a request
- toggling LLM planner usage
- viewing tools and models
- inspecting Harness JSON output

## Known Behavior

`python main.py run "check environment"` uses the planner by default. That means the command can wait on Ollama while the selected model loads or generates a JSON plan. For fast checks, use:

```bash
python main.py ready
python main.py run "check environment" --no-planner
```

## Recommended Next Steps

1. Add a `safe_shell` tool with an allowlist of commands.
2. Add run history storage for the web console.
3. Stream Harness phase updates to the UI instead of waiting for the final JSON response.
4. Improve planner prompts so simple tasks map directly to existing tools.
5. Add documentation for creating new tools safely.
