"""The agent loop — extended in Step 2 with tool use.

An "agent" is, at its core, a loop over a *growing message list*: each turn we
append the user's message, ask the model, then append the model's reply. Because
the whole list is sent every time, the model "remembers" earlier turns.

Step 2 adds the **agentic loop**: the model may answer with `tool_calls` instead
of text. When it does, we run each tool, append its result as a `tool` message,
and call the model again — repeating until it produces a final text answer. This
is what turns a chatbot into an agent.

Step 3 adds **AGENTS.md support**: if the project provides an `AGENTS.md` file
with conventions/instructions, we load it and append it to the system prompt.
This is just context injection — no retraining — yet it steers the agent's
behaviour for that project.

Step 4 adds **skills** with *progressive disclosure*: only each skill's name and
description go into the system prompt by default; the model pulls a skill's full
body into context on demand via the `load_skill` tool.

Step 5 adds **subagents**: via the `task` tool the agent spawns a fresh, isolated
Agent to handle a focused sub-task and gets back only its summary — keeping the
main context clean.
"""

import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent import fallback, permissions, skills, subagents, tools
from agent.client import get_client
from agent.config import OPENAI_MODEL, SYSTEM_PROMPT_PATH

# Safety cap: stop after this many model calls in a single turn so a misbehaving
# model can't loop on tools forever.
MAX_ITERATIONS = 10

# Small local models occasionally return a degenerate response: no tool calls
# *and* blank/whitespace content. It is intermittent, so we re-request a few
# times before giving up rather than showing the user an empty reply.
BLANK_RETRIES = 3

# Shown when the model keeps returning an empty response even after retries.
EMPTY_REPLY_NOTICE = "(The model returned an empty response — please try again.)"

# Filename holding project-specific instructions for the agent.
AGENTS_FILENAME = "AGENTS.md"

# Called as on_tool_event(name, arguments, result) after each tool runs, so a UI
# can show what happened. The Agent itself stays free of any printing.
ToolEvent = Callable[[str, dict, str], None]


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _find_agents_md(start: Path) -> Path | None:
    """Find the nearest AGENTS.md, searching `start` then its parent dirs.

    The project root is often above the working directory, so we walk upward and
    return the first AGENTS.md we find (or None).
    """
    for directory in (start, *start.parents):
        candidate = directory / AGENTS_FILENAME
        if candidate.is_file():
            return candidate
    return None


def _build_system_prompt(
    agents_md: Path | None, skill_library: skills.SkillLibrary
) -> str:
    """Base system prompt + the project's AGENTS.md + the skills catalog.

    Note the skills catalog carries only names and descriptions — never the skill
    bodies. Those are loaded on demand (progressive disclosure).
    """
    prompt = _load_system_prompt()
    if agents_md is not None:
        instructions = agents_md.read_text(encoding="utf-8")
        prompt += (
            f"\n\n# Project instructions (from {AGENTS_FILENAME})\n\n"
            "The project provides the following instructions. Treat them as "
            "authoritative and follow them.\n\n"
            f"{instructions}"
        )
    if skill_library:
        prompt += "\n\n" + skill_library.catalog()
    return prompt


class Agent:
    """Holds the conversation history and runs the agentic loop.

    `depth` is the delegation level: 0 is the top-level agent, and each subagent
    spawned via the `task` tool is one deeper. It gates further delegation.
    """

    def __init__(self, depth: int = 0) -> None:
        self.depth = depth
        self.client = get_client()
        # Discover project instructions (AGENTS.md) and skills from the cwd.
        self.agents_md_path = _find_agents_md(Path.cwd())
        self.skills = skills.SkillLibrary(skills.discover_skills(Path.cwd()))
        # The tools offered to the model: the static ones, plus load_skill when
        # the project has skills, plus `task` when we may still delegate deeper.
        self.tools: list[dict] = [*tools.TOOLS]
        if self.skills:
            self.tools.append(skills.LOAD_SKILL_TOOL)
        self.can_delegate = depth < subagents.MAX_DEPTH
        if self.can_delegate:
            self.tools.append(subagents.TASK_TOOL)
        # The growing message list. It starts with the system prompt and gains
        # user, assistant, and `tool` messages as the conversation proceeds.
        system = _build_system_prompt(self.agents_md_path, self.skills)
        if depth > 0:
            system += subagents.SUBAGENT_SYSTEM_NOTE
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": system}]

    def _complete(self) -> Any:
        """Call the model, retrying if it returns a blank, no-tool response.

        The local model sometimes glitches and answers with neither text nor a
        tool call. Since it is intermittent, re-requesting usually fixes it; we
        return the first non-blank message, or the last one if all were blank.
        """
        message = None
        for _ in range(BLANK_RETRIES):
            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=self.messages,  # type: ignore[arg-type]  # plain dicts; SDK wants TypedDicts
                tools=self.tools,  # type: ignore[arg-type]
            )
            message = response.choices[0].message
            if message.tool_calls or (message.content or "").strip():
                return message
        return message

    def _tool_names(self) -> set[str]:
        return {t["function"]["name"] for t in self.tools}

    def _dispatch_tool(
        self,
        name: str,
        arguments: dict,
        on_tool_event: ToolEvent | None,
        approve: permissions.ApprovalCallback | None,
    ) -> str:
        """Run one tool call and report it. load_skill and task need this
        session's state; everything else goes to the stateless dispatcher.

        Side-effecting tools must be approved first; a denied call is reported
        back to the model so it can react instead of silently failing.
        """
        if (
            approve is not None
            and name in permissions.TOOLS_REQUIRING_APPROVAL
            and not approve(name, arguments)
        ):
            result = permissions.DENIED_RESULT
            if on_tool_event is not None:
                on_tool_event(name, arguments, result)
            return result

        if name == "load_skill":
            result = self.skills.load(arguments.get("name", ""))
        elif name == "task":
            result = self._run_subagent(
                arguments.get("description", ""), on_tool_event, approve
            )
        else:
            result = tools.execute_tool(name, arguments)
        if on_tool_event is not None:
            on_tool_event(name, arguments, result)
        return result

    def chat(
        self,
        user_message: str,
        on_tool_event: ToolEvent | None = None,
        approve: permissions.ApprovalCallback | None = None,
    ) -> str:
        """Run one turn, looping over tool calls until the model answers."""
        self.messages.append({"role": "user", "content": user_message})

        for _ in range(MAX_ITERATIONS):
            message = self._complete()

            # We only register function tools, so keep just those calls (the SDK
            # union also allows custom tool calls). This also narrows the type.
            calls = [tc for tc in (message.tool_calls or []) if tc.type == "function"]

            if not calls:
                # No native tool calls. The local model sometimes emits a call as
                # text instead — try to recover it before treating this as final.
                recovered = fallback.parse_text_tool_call(
                    message.content, self._tool_names()
                )
                if recovered is None:
                    reply = message.content or ""
                    self.messages.append({"role": "assistant", "content": reply})
                    # Don't show the user a blank line if it came back empty.
                    return reply if reply.strip() else EMPTY_REPLY_NOTICE
                # Normalise the text call into a proper tool-call/result pair so
                # the history stays well-formed and the loop continues.
                name, arguments = recovered
                call_id = f"fallback-{uuid.uuid4().hex[:8]}"
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": call_id,
                                "type": "function",
                                "function": {
                                    "name": name,
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ],
                    }
                )
                result = self._dispatch_tool(name, arguments, on_tool_event, approve)
                self.messages.append(
                    {"role": "tool", "tool_call_id": call_id, "content": result}
                )
                continue

            # Native path: record the assistant's request (with its tool_calls),
            # then run each tool and append its result.
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
                result = self._dispatch_tool(name, arguments, on_tool_event, approve)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "(stopped: reached the tool-call limit for this turn)"

    def _run_subagent(
        self,
        description: str,
        on_tool_event: ToolEvent | None,
        approve: permissions.ApprovalCallback | None,
    ) -> str:
        """Spawn a fresh, isolated Agent for one task and return its summary.

        The subagent has its own message list (it cannot see this conversation),
        so only the `description` and its tools inform it — and only its final
        reply comes back. We forward its tool events with a `↳` marker so the
        nested work is visible, and pass `approve` down so the subagent's
        side-effecting tools are gated too.
        """
        subagent = Agent(depth=self.depth + 1)

        def sub_event(tool_name: str, args: dict, result: str) -> None:
            # No-op if the parent isn't displaying a trace.
            if on_tool_event is not None:
                on_tool_event(f"↳ {tool_name}", args, result)

        return subagent.chat(description, on_tool_event=sub_event, approve=approve)
