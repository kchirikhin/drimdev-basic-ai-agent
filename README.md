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
> the agent from. A permission/approval layer arrives in Step 6 — until then,
> sandbox the agent (see below).

### Running it safely (OS-level sandbox)

To stop the agent from touching anything outside one directory, run it under
**bubblewrap** with the included wrapper. The system is mounted read-only, the
rest of your home is hidden, and only the given directory is writable — so
`execute`/`write`/`delete` physically cannot escape it. Network stays up so the
model is still reachable.

```bash
sudo apt install bubblewrap          # if not already installed
./run-sandboxed.sh ~/agent-work      # only ~/agent-work is writable (default: ./sandbox)
```

Model/endpoint come from the usual env vars, e.g.
`OPENAI_MODEL=qwen2.5:7b-instruct ./run-sandboxed.sh ~/agent-work`. This is an
external guard independent of the agent's own (later) permission system.

> **Note on models:** the tools require a model that emits native OpenAI
> `tool_calls`. `qwen2.5:7b-instruct` works well in Ollama; the `qwen2.5-coder`
> models do *not* reliably emit tool calls. Set `OPENAI_MODEL` accordingly.

## Step 3 — AGENTS.md

On startup the agent looks for an `AGENTS.md` file — in the working directory,
then walking up to parent directories — and appends its contents to the system
prompt. This is plain context injection (no retraining), but it lets a project
steer the agent's behaviour: coding conventions, what to do or avoid, etc. When
one is found, the CLI prints `Loaded project instructions from <path>`.

For example, an `AGENTS.md` containing "Always use 4-space indentation and add
type hints" will shape how the agent writes code in that project.

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
poetry run pytest                       # run the test suite
```

Tests live in `tests/` and cover each tool (`tests/test_tools.py`). They run
against a temporary directory, so they never touch your real files.

Tool configuration lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`); the
hook definitions are in `.pre-commit-config.yaml`.
