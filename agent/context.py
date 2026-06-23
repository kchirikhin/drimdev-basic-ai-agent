"""Context-usage summary for the `context` REPL command.

Breaks the agent's message list down by role with an approximate token count, so
you can see how full the context is. A handy way to confirm that delegating to a
subagent does not bloat the main context: only the `task` call and the returned
summary land here — never the subagent's internal tool I/O.

The token figure is a rough estimate (the local model's tokenizer is not the
OpenAI one), good enough to compare sizes and spot bloat.
"""

import dataclasses

# Rough characters-per-token heuristic for the estimate.
CHARS_PER_TOKEN = 4

# Roles shown first, in this order; any others are appended after.
ROLE_ORDER = ["system", "user", "assistant", "tool"]


@dataclasses.dataclass
class RoleStat:
    count: int = 0
    tokens: int = 0


@dataclasses.dataclass
class ContextSummary:
    by_role: dict[str, RoleStat]
    total_messages: int
    total_tokens: int


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def _message_text(message: dict) -> str:
    """All text that counts toward context: content plus any tool-call payload."""
    parts = []
    content = message.get("content")
    if content:
        parts.append(content)
    for call in message.get("tool_calls") or []:
        function = call.get("function", {})
        parts.append(function.get("name", ""))
        parts.append(function.get("arguments", ""))
    return "".join(parts)


def summarize_messages(messages: list[dict]) -> ContextSummary:
    by_role: dict[str, RoleStat] = {role: RoleStat() for role in ROLE_ORDER}
    total_tokens = 0
    for message in messages:
        role = message.get("role", "?")
        tokens = _estimate_tokens(_message_text(message))
        stat = by_role.setdefault(role, RoleStat())
        stat.count += 1
        stat.tokens += tokens
        total_tokens += tokens
    return ContextSummary(
        by_role=by_role,
        total_messages=len(messages),
        total_tokens=total_tokens,
    )


def format_summary(summary: ContextSummary, window: int | None = None) -> str:
    """Render the summary as plain text (the CLI adds colour)."""
    ordered = ROLE_ORDER + [r for r in summary.by_role if r not in ROLE_ORDER]
    lines = ["Context usage:"]
    for role in ordered:
        stat = summary.by_role.get(role)
        if stat and stat.count:
            lines.append(f"  {role:<10} {stat.count:>3} msg   ≈ {stat.tokens:>6} tok")
    lines.append("  " + "-" * 32)
    total = (
        f"  {'total':<10} {summary.total_messages:>3} msg   "
        f"≈ {summary.total_tokens:>6} tok"
    )
    if window:
        total += f"   ({100 * summary.total_tokens / window:.1f}% of {window})"
    lines.append(total)
    return "\n".join(lines)
