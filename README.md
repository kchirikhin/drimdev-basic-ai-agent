# drimdev-basic-ai-agent

A minimal coding agent (in the spirit of Claude Code) built **from scratch for
learning**. The goal is to grasp the core ideas behind such agents by
re-implementing them step by step. See [SPEC.md](SPEC.md) for the full roadmap.

The agent talks to a **local, OpenAI-compatible LLM** (default: Ollama with
`qwen2.5-coder:7b`).

## Step 1 — Agent loop

A stateful conversation loop. An "agent" is fundamentally a loop over a *growing
message list* — each turn appends the user's message, calls the model, and
appends the reply, so the model remembers earlier turns.

## Step 2 — Tools

The agent can now *act*, using the **OpenAI function-calling protocol**. The tool
schemas are sent with each request; when the model returns a `tool_call`, the
host runs the matching function and feeds the result back as a `tool` message,
looping until the model produces a final answer (see `agent/loop.py` and
`agent/tools.py`). The CLI prints a grey `⚙` trace of each tool call.

Available tools: `read`, `write`, `update` (replace text in place), `delete`,
`list`, `execute` (run a shell command).

> ⚠️ **No permissions yet.** The file tools modify the real filesystem and
> `execute` runs arbitrary shell commands, both in the directory you launched
> the agent from. Run it in a scratch directory. A permission/approval layer
> arrives in Step 6.

> **Note on models:** the tools require a model that emits native OpenAI
> `tool_calls`. `qwen2.5:7b-instruct` works well in Ollama; the `qwen2.5-coder`
> models do *not* reliably emit tool calls. Set `OPENAI_MODEL` accordingly.

## Setup

1. Install dependencies:

   ```bash
   poetry install
   ```

2. (Optional) Configure the backend. The defaults target a local Ollama server,
   so if you run Ollama with `qwen2.5-coder:7b` you can skip this. Otherwise:

   ```bash
   cp .env.example .env   # then edit OPENAI_BASE_URL / OPENAI_API_KEY / OPENAI_MODEL
   ```

   | Variable          | Default                       |
   | ----------------- | ----------------------------- |
   | `OPENAI_BASE_URL` | `http://localhost:11434/v1`   |
   | `OPENAI_API_KEY`  | `ollama`                      |
   | `OPENAI_MODEL`    | `qwen2.5-coder:7b`           |

3. Run the agent:

   ```bash
   poetry run agent
   ```

## Example session

```text
You: My name is Kon.
Agent: Nice to meet you, Kon! How can I help you today?

You: What is my name?
Agent: Your name is Kon.
```

Type `exit` (or press `Ctrl-C`) to quit.

## Development

Code quality is enforced with **Ruff** (lint + format) and **mypy** (type
checking), wired together via **pre-commit**.

After `poetry install`, enable the git hook once:

```bash
poetry run pre-commit install
```

The hooks then run automatically on every `git commit`. To run them by hand:

```bash
poetry run pre-commit run --all-files   # all hooks on the whole repo
poetry run ruff format                  # format
poetry run ruff check --fix             # lint (with autofix)
poetry run mypy agent                   # type-check
```

Tool configuration lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`); the
hook definitions are in `.pre-commit-config.yaml`.
