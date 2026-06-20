"""The agent loop — the heart of Step 1.

An "agent" is, at its core, a loop over a *growing message list*: each turn we
append the user's message, ask the model, then append the model's reply. Because
the whole list is sent every time, the model "remembers" earlier turns.

There are no tools yet (that is Step 2), so each turn is a single model call.
"""

from agent.client import get_client
from agent.config import OPENAI_MODEL, SYSTEM_PROMPT_PATH


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


class Agent:
    """Holds the conversation history and talks to the model."""

    def __init__(self) -> None:
        self.client = get_client()
        # The growing message list. It starts with the system prompt and gains
        # a user + assistant message on every turn.
        self.messages: list[dict] = [
            {"role": "system", "content": _load_system_prompt()}
        ]

    def chat(self, user_message: str) -> str:
        """Run one turn of the loop and return the assistant's reply."""
        self.messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=self.messages,
        )
        reply = response.choices[0].message.content

        self.messages.append({"role": "assistant", "content": reply})
        return reply
