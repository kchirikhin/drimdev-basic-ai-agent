# SPEC — Basic AI Coding Agent

## Purpose

A minimal coding agent (in the spirit of Claude Code) built **from scratch for
learning**. The goal is not to ship a product but to understand, by
re-implementing them, the core ideas that make tools like Claude Code work — the
agent loop, tool use, project instructions, skills, subagents, and permissions.

Building each piece by hand should make us more advanced and proficient *users*
of such tools.

## Principles

- **Learning over completeness.** Prefer small, readable implementations that
  expose the mechanism over robust, feature-complete ones that hide it.
- **One concept per step.** Each step adds exactly one capability and stays
  runnable end-to-end.
- **Stay close to the metal.** No agent frameworks. Talk to the model directly
  via the OpenAI Python SDK so nothing important is hidden behind abstractions.
- **Local-first.** Everything runs against a local, OpenAI-compatible LLM. No
  cloud account required.

## Tech stack

- **Language:** Python 3.10+
- **Dependency management:** Poetry
- **LLM access:** `openai` Python SDK pointed at an OpenAI-compatible endpoint.
- **Default backend:** [Ollama](https://ollama.com) at `http://localhost:11434/v1`
  with model `qwen2.5-coder:7b` (matches the lab1 setup). Any OpenAI-compatible
  server (LM Studio, llama.cpp, vLLM, …) works by changing `base_url`/`model`.

### Configuration

The agent reads its backend config from environment variables (with the defaults
above):

| Variable          | Default                        | Meaning                          |
| ----------------- | ------------------------------ | -------------------------------- |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1`    | OpenAI-compatible endpoint       |
| `OPENAI_API_KEY`  | `ollama`                       | API key (placeholder for local)  |
| `OPENAI_MODEL`    | `qwen2.5-coder:7b`             | Model name                       |

`OPENAI_BASE_URL` and `OPENAI_API_KEY` are the standard variables the `openai`
SDK reads automatically; `OPENAI_MODEL` is our own convention (the SDK has no
model variable).

## Roadmap

Six steps, each runnable on its own and building on the previous. Details are
intentionally left to emerge during implementation; what matters per step is the
**learning goal**.

### Step 1 — Agent loop

The heart of any agent: a loop that sends the conversation to the model, gets a
reply, appends it to the history, and repeats. Stateful conversation (unlike
lab1's stateless `ask`).

- **Learning goal:** see that an "agent" is fundamentally a `while` loop over a
  growing message list, plus a system prompt.
- **Done when:** you can hold a multi-turn conversation in the terminal and the
  model remembers earlier turns.

### Step 2 — Tools support

Give the model the ability to act, not just talk. Define a few file/shell tools,
expose them to the model via the OpenAI tool-calling API, execute requested
calls, and feed results back into the loop.

- **Learning goal:** understand the tool-use cycle — model requests a tool, host
  runs it, result returns as a `tool` message, model continues. This is what
  turns a chatbot into an agent.
- **Initial toolset:** read file, write/edit file, list directory, run shell
  command.
- **Done when:** the agent can complete a small task (e.g. "create a file and
  run it") by calling tools on its own.

### Step 3 — AGENTS.md support

Load project-level instructions from an `AGENTS.md` file (the open analogue of
`CLAUDE.md`) and inject them into the system prompt so the agent respects
project conventions.

- **Learning goal:** understand how project memory/instructions steer an agent
  without retraining — it's just context injection.
- **Done when:** placing an `AGENTS.md` in the working directory measurably
  changes the agent's behavior.

### Step 4 — Skills support

Add reusable, named "skills" — packaged instructions (and optionally helper
files) the agent can discover and load on demand, instead of stuffing everything
into the system prompt.

- **Learning goal:** understand progressive disclosure — keep the base prompt
  small and pull in specialized know-how only when relevant.
- **Done when:** the agent can list available skills and apply one when a task
  matches it.

### Step 5 — Subagents support

Let the main agent spawn a fresh, isolated agent (its own context window and
loop) to handle a focused sub-task, then return only the result.

- **Learning goal:** understand context isolation and delegation — why farming
  out a noisy sub-task keeps the main context clean.
- **Done when:** the main agent can delegate a task to a subagent and use its
  summarized result.

### Step 6 — Permissions support

Gate side-effecting tools (write, shell) behind user approval, with modes like
ask / allow / deny and optional per-tool rules.

- **Learning goal:** understand the safety/control layer — how an agent stays
  under human control while still being autonomous.
- **Done when:** dangerous actions prompt for confirmation, and the user can
  allow/deny per call (and ideally remember the choice).

## Out of scope

Streaming UI polish, multi-provider abstraction layers, persistence/databases,
test coverage of the model itself, and production hardening. These can be added
later but are not learning goals here.
