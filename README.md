# NestAgent

Pure-Python agent **harness** (runtime engine). The LLM (Ollama) is **planner only**; the harness owns decisions, tool execution, validation, and GitHub discovery.

## Current Status

NestAgent currently includes:

- Ollama-backed JSON planner.
- Harness workflow: plan, review, execute, validate.
- Environment readiness validation.
- Tool registry with `echo`, `environment_check`, `list_dir`, and `read_file`.
- Safe filesystem access constrained to the project root.
- GitHub discovery module for open-source lookup before new tool creation.
- Local web console with dynamic port handling.
- Tests for registry, validation, filesystem safety, and web port selection.

See [`docs/PROJECT_SUMMARY.md`](docs/PROJECT_SUMMARY.md) for the full project summary and next steps.

## Architecture

| Layer | Role |
| ------- | ------ |
| **LLM** (`llm/`) | Planning JSON only — no tool execution |
| **Harness** (`harness/`) | Workflow, validation, retries, orchestration |
| **Tools** (`tools/`) | Reusable capabilities + registry |
| **Discovery** (`discovery/`) | GitHub search before new tools |

No LangChain / LangGraph / CrewAI.

## Quick start

```bash
cd /Users/ali.abdulhafez/AiLab/NestAgent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Ollama must be running
ollama serve   # if not already up

python main.py ready
python main.py tools
python main.py models
python main.py run "check environment" --no-planner
python main.py run "list project files and read README.md"
python main.py run "summarize what NestAgent does"

# Local web console. Defaults to port 18080, and auto-falls back if busy.
python main.py web
python main.py web --port 0
```

`python main.py run "..."` uses the LLM planner by default. If Ollama is slow or the model is cold, use `--no-planner` for direct tool execution.

## Configuration (environment)

| Variable | Default |
| ---------- | ------- |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` |
| `NESTAGENT_PLANNER_MODEL` | `qwen2.5-coder:7b` |
| `NESTAGENT_MAX_RETRIES` | `2` |
| `NESTAGENT_WEB_HOST` | `127.0.0.1` |
| `NESTAGENT_WEB_PORT` | `18080` |

## Project layout

```text
config/       settings
harness/      engine, workflow, validation
llm/          Ollama client + planner
tools/        base, registry, builtins
discovery/    GitHub search
web/          local browser console
tests/
main.py       CLI
```

## Cursor Rule

Project guidance lives in `.cursor/rules/nestagent-architecture.mdc`. It keeps future agent work aligned with the Harness rules: Step 0 readiness checks, planner-only LLM usage, registry-first tools, GitHub discovery before new tools, and stdlib-first Python.

## Tests

```bash
pytest
```
