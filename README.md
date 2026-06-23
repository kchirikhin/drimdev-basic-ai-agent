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
>
> Even good local models occasionally emit a tool call as JSON *text* instead of
> a native call. The system prompt avoids listing tools in text (which reduces
> this), and `agent/fallback.py` recovers the common `{name, arguments}` shape
> when it still happens — so the agent keeps working. Native calls stay the
> primary path.

## Step 3 — AGENTS.md

On startup the agent looks for an `AGENTS.md` file — in the working directory,
then walking up to parent directories — and appends its contents to the system
prompt. This is plain context injection (no retraining), but it lets a project
steer the agent's behaviour: coding conventions, what to do or avoid, etc. When
one is found, the CLI prints `Loaded project instructions from <path>`.

For example, an `AGENTS.md` containing "Always use 4-space indentation and add
type hints" will shape how the agent writes code in that project.

## Step 4 — Skills

Skills are packaged, reusable instructions the agent loads **on demand**. They
live in a `skills/` directory (searched from the working directory upward); each
skill is a folder with a `SKILL.md` — frontmatter (`name`, `description`) plus a
body of instructions:

```
skills/
  commit-message/
    SKILL.md
```

The key idea is **progressive disclosure**: by default only each skill's *name
and description* go into the system prompt. The full body is fetched only when
the model calls the `load_skill` tool because a task matches — so the base prompt
stays small while specialized know-how is available when needed. The CLI lists
discovered skills on startup, and you'll see a `⚙ load_skill(...)` trace when one
is pulled in. An example `commit-message` skill ships in `skills/`.

## Step 5 — Subagents

The agent can delegate a focused sub-task to a **subagent** via the `task` tool.
A subagent is a fresh `Agent` with its **own isolated context**, its own agentic
loop, and the same tools. It runs the task to completion and returns only a
short summary — so the parent's context never fills up with the subagent's
intermediate steps (the whole point: farm out a noisy sub-task to keep the main
conversation clean).

In the trace, the subagent's own tool calls are shown with a `↳` marker, and the
delegating `⚙ task(...)` call shows the summary that comes back. Delegation depth
is capped (`subagents.MAX_DEPTH`) so subagents can't spawn endlessly.

Type **`context`** in the REPL to see the current context usage broken down by
role with an approximate token count. It's a good way to *see* the isolation:
after a subagent runs many tools, the main context grows only by the `task` call
and its one-line summary — not by the subagent's internal steps. (The token
figure is an estimate; the window for the percentage is `OPENAI_CONTEXT_WINDOW`,
default 32768.)

## Step 6 — Permissions

Side-effecting tools — `write`, `delete`, and `execute` — now ask for approval
before they run. Before such a tool runs, the agent calls an approval callback;
the CLI prompts you:

```
Allow write({"path": "greet.txt", "content": "hello"})? [y]es / [n]o / [a]lways:
```

- **y** — allow this one call.
- **n** — deny it; the model is told the call was denied and can adapt.
- **a** — allow and *remember* this tool for the rest of the session (stops
  asking for it).

Which tools are gated is the policy in `agent/permissions.py` (add `update`
there if you want in-place edits gated too). The check is enforced in the
`Agent`, and the approval callback is passed down into subagents, so a
subagent's `write`/`execute`/`delete` calls are gated as well. This is the
safety/control layer — the agent stays autonomous, but you keep a veto. It is
complementary to the OS-level sandbox (`run-sandboxed.sh`): permissions are a
per-call human check, the sandbox is a hard boundary.

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

Agent replies are rendered as **Markdown** in the terminal (via `rich`) —
headings, bold, lists, and syntax-highlighted code blocks. It falls back to plain
text automatically when output isn't a terminal (e.g. piped to a file).

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
