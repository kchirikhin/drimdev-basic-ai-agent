"""Fallback parsing of tool calls emitted as text (model robustness).

Small local models sometimes put a tool call in the message *content* as JSON
instead of using the native tool-calling API. When that happens — and only then —
we try to recover by parsing the common `{"name": ..., "arguments": {...}}` shape
(raw, fenced in ```json, or embedded in prose) and running it as if it were a
native call.

This is a best-effort safety net for one widespread convention, not a universal
parser: it does not understand other formats (Python-style calls, `<tool_call>`
tags, etc.). It stays subordinate to native tool calls and is deliberately
conservative — it only fires when the JSON parses cleanly into the expected shape
*and* names a tool we actually have, so a normal answer that merely mentions JSON
is not hijacked.
"""

import json
import re
from collections.abc import Iterator

# A ```json ... ``` (or plain ``` ... ```) fenced block; captures the inner text.
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _candidates(content: str) -> Iterator[str]:
    """Yield substrings of `content` that might be the JSON tool call."""
    text = content.strip()
    # 1) the whole message is the JSON object
    yield text
    # 2) any fenced code block (handles "Sure!\n```json\n{...}\n```")
    for match in _FENCE.finditer(content):
        yield match.group(1).strip()
    # 3) from the first '{' to the last '}' (handles a stray prefix like "ḷ\n{")
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        yield text[start : end + 1]


def parse_text_tool_call(
    content: str | None, known_names: set[str]
) -> tuple[str, dict] | None:
    """Recover a tool call from text, or return None.

    Returns `(name, arguments)` only when some candidate parses as a JSON object
    of the form `{"name": <known tool>, "arguments": {...}}` (the `arguments` may
    itself be a JSON string, and `parameters` is accepted as an alias).
    """
    if not content:
        return None
    for candidate in _candidates(content):
        call = _try_object(candidate, known_names)
        if call is not None:
            return call
    return None


def _try_object(text: str, known_names: set[str]) -> tuple[str, dict] | None:
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    name = data.get("name")
    if not isinstance(name, str) or name not in known_names:
        return None

    arguments = data.get("arguments", data.get("parameters", {}))
    if isinstance(arguments, str):  # arguments may be a nested JSON string
        try:
            arguments = json.loads(arguments)
        except (ValueError, TypeError):
            return None
    if not isinstance(arguments, dict):
        return None

    return name, arguments
