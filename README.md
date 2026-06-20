# drimdev-basic-ai-agent

A minimal coding agent (in the spirit of Claude Code) built **from scratch for
learning**. The goal is to grasp the core ideas behind such agents by
re-implementing them step by step. See [SPEC.md](SPEC.md) for the full roadmap.

The agent talks to a **local, OpenAI-compatible LLM** (default: Ollama with
`qwen2.5-coder:7b`).

## Step 1 — Agent loop

The current code implements the heart of any agent: a stateful conversation
loop. An "agent" is fundamentally a loop over a *growing message list* — each
turn appends the user's message, calls the model, and appends the reply, so the
model remembers earlier turns. No tools yet (that's Step 2).

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
