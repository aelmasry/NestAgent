# NestAgent

Pure-Python agent **harness** (runtime engine). The LLM (Ollama) is **planner only**; the harness owns decisions, tool execution, validation, and GitHub discovery.

## Architecture

| Layer | Role |
|-------|------|
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
python main.py models
python main.py run "check environment" --no-planner
python main.py run "summarize what NestAgent does"
```

## Configuration (environment)

| Variable | Default |
|----------|---------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` |
| `NESTAGENT_PLANNER_MODEL` | `qwen2.5-coder:7b` |
| `NESTAGENT_MAX_RETRIES` | `2` |

## Project layout

```
config/       settings
harness/      engine, workflow, validation
llm/          Ollama client + planner
tools/        base, registry, builtins
discovery/    GitHub search
tests/
main.py       CLI
```

## Tests

```bash
pytest
```
