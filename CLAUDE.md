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

## Conventions

- Keep dependencies minimal; add them via `poetry add`.
- Code and identifiers in English; comments only where they aid understanding.
- Keep each step's entrypoint working — don't break earlier steps when adding a
  new one.
