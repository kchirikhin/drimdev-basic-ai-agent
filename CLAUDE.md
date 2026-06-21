# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Overview

A learning project that builds a minimal coding agent (à la Claude Code) **from
scratch** to understand how such agents work internally. See `SPEC.md` for the
full goals and the six-step roadmap. Docs and user-facing strings are in
**English**.

The agent talks to a **local, OpenAI-compatible LLM** via the `openai` Python
SDK. Default backend: Ollama at `http://localhost:11434/v1` with
`qwen2.5-coder:7b`.

## Development is step-by-step

The project is built in six incremental steps (see `SPEC.md`). Each step adds
exactly **one** capability and must stay runnable end-to-end:

1. Agent loop
2. Tools support
3. AGENTS.md support
4. Skills support
5. Subagents support
6. Permissions support

When implementing, respect the current step's scope. Favor small, readable code
that exposes the mechanism over robust code that hides it — this is a teaching
codebase. Don't pull in agent frameworks; keep the model interaction explicit.

### Code map

- `agent/loop.py` — `Agent` class and the agentic loop (Steps 1–2): grows the
  message list, and when the model returns `tool_calls`, runs each tool and
  feeds results back until the model answers with text.
- `agent/tools.py` — the six tools (`read`/`write`/`update`/`delete`/`list`/
  `execute`) as OpenAI function-calling schemas plus an `execute_tool`
  dispatcher. Tools are intentionally unsandboxed until Step 6.
- `agent/cli.py` — REPL, spinner, and the grey `⚙` tool-call trace.
- `agent/client.py`, `agent/config.py` — OpenAI client factory and env config.

Tool calling needs a model that emits native `tool_calls` (e.g.
`qwen2.5:7b-instruct`); `qwen2.5-coder` does not, despite advertising the
capability.

## Environment & running

Python 3.10+ with Poetry for dependency management.

```bash
poetry install          # install dependencies
poetry run <entrypoint> # run the agent (entrypoint added in step 1)
```

Configuration is via environment variables (defaults match a local Ollama
setup):

| Variable          | Default                       |
| ----------------- | ----------------------------- |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1`   |
| `OPENAI_API_KEY`  | `ollama`                      |
| `OPENAI_MODEL`    | `qwen2.5-coder:7b`           |

`OPENAI_BASE_URL` and `OPENAI_API_KEY` are read automatically by the `openai`
SDK; `OPENAI_MODEL` is our own convention.

A local Ollama server with the `qwen2.5-coder:7b` model must be running and
reachable for the defaults to work. Any OpenAI-compatible endpoint works by
overriding the variables above.

## Code quality

Ruff (lint + format) and mypy (type checking) run via pre-commit. Before
finishing any change, make sure they pass:

```bash
poetry run ruff format && poetry run ruff check --fix && poetry run mypy agent
```

Config is in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`) and
`.pre-commit-config.yaml`. The hooks call `poetry run ...` so versions match the
project. Keep the code mypy-clean; prefer fixing types over broad ignores.

## Conventions

- Keep dependencies minimal; add them via `poetry add` (dev tools via
  `poetry add --group dev`).
- Code and identifiers in English; comments only where they aid understanding.
- Keep each step's entrypoint working — don't break earlier steps when adding a
  new one.
