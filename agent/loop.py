"""The agent loop — extended in Step 2 with tool use.

An "agent" is, at its core, a loop over a *growing message list*: each turn we
append the user's message, ask the model, then append the model's reply. Because
the whole list is sent every time, the model "remembers" earlier turns.

Step 2 adds the **agentic loop**: the model may answer with `tool_calls` instead
of text. When it does, we run each tool, append its result as a `tool` message,
and call the model again — repeating until it produces a final text answer. This
is what turns a chatbot into an agent.
"""

import json
from collections.abc import Callable
from typing import Any

from agent import tools
from agent.client import get_client
from agent.config import OPENAI_MODEL, SYSTEM_PROMPT_PATH

# Safety cap: stop after this many model calls in a single turn so a misbehaving
# model can't loop on tools forever.
MAX_ITERATIONS = 10

# Called as on_tool_event(name, arguments, result) after each tool runs, so a UI
# can show what happened. The Agent itself stays free of any printing.
ToolEvent = Callable[[str, dict, str], None]


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class Agent:
    """Holds the conversation history and runs the agentic loop."""

    def __init__(self) -> None:
        self.client = get_client()
        # The growing message list. It starts with the system prompt and gains
        # user, assistant, and `tool` messages as the conversation proceeds.
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": _load_system_prompt()}
        ]

    def chat(self, user_message: str, on_tool_event: ToolEvent | None = None) -> str:
        """Run one turn, looping over tool calls until the model answers."""
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_ITERATIONS):
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=self.messages,  # type: ignore[arg-type]  # plain dicts; SDK wants TypedDicts
                tools=tools.TOOLS,  # type: ignore[arg-type]
            )
            message = response.choices[0].message

            # No tool calls => the model produced its final answer.
            if not message.tool_calls:
                reply = message.content or ""
                self.messages.append({"role": "assistant", "content": reply})
                return reply

            # We only register function tools, so keep just those calls (the SDK
            # union also allows custom tool calls). This also narrows the type.
            calls = [tc for tc in message.tool_calls if tc.type == "function"]

            # Record the assistant's request (including the tool_calls the next
            # messages will answer), then run each tool.
            self.messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in calls
                    ],
                }
            )

            for tool_call in calls:
                name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments or "{}")
                result = tools.execute_tool(name, arguments)
                if on_tool_event is not None:
                    on_tool_event(name, arguments, result)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "(stopped: reached the tool-call limit for this turn)"
