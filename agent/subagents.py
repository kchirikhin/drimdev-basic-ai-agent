"""Subagents — delegation with context isolation (Step 5).

The main agent can spawn a *subagent*: a fresh `Agent` with its own message list,
its own agentic loop, and the same tools. It runs one focused sub-task to
completion and returns only its final summary. The subagent's intermediate steps
(its tool calls, dead ends, long file dumps) stay in *its* context and never
pollute the parent's — that is the whole point: farm out a noisy sub-task to keep
the main conversation clean.

This module holds just the metadata (the `task` tool schema, the depth limit, and
the subagent system note). The actual spawning lives in `loop.py` (the `Agent`
creates another `Agent`), which avoids an import cycle.
"""

# How deep delegation may nest. With 1, the main agent (depth 0) can spawn
# subagents (depth 1), but those subagents do not get the `task` tool — so they
# cannot spawn further. This keeps things simple and prevents runaway recursion.
MAX_DEPTH = 1

# Appended to a subagent's system prompt so it knows its role.
SUBAGENT_SYSTEM_NOTE = (
    "\n\n# You are a subagent\n\n"
    "You were spawned to handle one focused task. You cannot see the parent "
    "conversation, so rely only on the task description and your tools. Do the "
    "work, then reply with a concise summary of the outcome, including any "
    "results the caller needs."
)

# The tool the main agent calls to delegate. Only offered when depth < MAX_DEPTH.
TASK_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "task",
        "description": (
            "Delegate a focused, self-contained sub-task to a fresh subagent "
            "that has its own isolated context and the same tools. Use this for "
            "big or noisy sub-tasks (exploring many files, a multi-step chore) to "
            "keep your own context clean. The subagent cannot see this "
            "conversation, so write a complete description. Returns only the "
            "subagent's final summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": (
                        "A complete, self-contained description of the task for "
                        "the subagent."
                    ),
                }
            },
            "required": ["description"],
        },
    },
}
