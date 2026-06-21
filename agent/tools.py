"""Tools the agent can call — the heart of Step 2.

Tools are exposed to the model with the OpenAI function-calling protocol: each
tool is described as a JSON schema (`TOOLS`) and passed to the API. When the
model decides to use one, the API returns a structured `tool_call` (name +
JSON arguments) instead of plain text. The host runs the matching Python
function and feeds the result back as a `tool` message; see `agent/loop.py`.

This module has three parts:
1. the implementations (`_read`, `_write`, ...),
2. the `TOOLS` schemas sent to the model,
3. the `execute_tool` dispatcher that runs a call by name.

SAFETY: there is no permission system or sandbox yet (that is Step 6). The file
tools touch the real filesystem and `execute` runs arbitrary shell commands,
both relative to the directory the agent was launched from. Intentional for now.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

# `execute` is killed if it runs longer than this many seconds.
EXECUTE_TIMEOUT = 30


# --------------------------------------------------------------------------- #
# Implementations. Each returns a human-readable string that goes back to the
# model. They raise on failure; `execute_tool` turns exceptions into error
# strings so a bad call never crashes the loop.
# --------------------------------------------------------------------------- #


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _write(path: str, content: str) -> str:
    p = Path(path)
    p.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {path}"


def _update(path: str, old_text: str, new_text: str) -> str:
    p = Path(path)
    original = p.read_text(encoding="utf-8")
    count = original.count(old_text)
    if count == 0:
        raise ValueError(f"old_text not found in {path}")
    p.write_text(original.replace(old_text, new_text), encoding="utf-8")
    return f"Replaced {count} occurrence(s) in {path}"


def _delete(path: str) -> str:
    Path(path).unlink()
    return f"Deleted {path}"


def _list(path: str = ".") -> str:
    entries = sorted(Path(path).iterdir(), key=lambda e: e.name)
    if not entries:
        return f"{path} is empty"
    return "\n".join(e.name + ("/" if e.is_dir() else "") for e in entries)


def _execute(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=EXECUTE_TIMEOUT,
    )
    parts = [f"exit code: {result.returncode}"]
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Tool schemas in OpenAI function-calling format. These are what the model sees.
# --------------------------------------------------------------------------- #

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read and return the contents of a text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Create a file or overwrite it with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "content": {
                        "type": "string",
                        "description": "Full content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update",
            "description": (
                "Edit an existing file in place by replacing every occurrence of "
                "old_text with new_text. Use a snippet of old_text long enough to "
                "be unique."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to find.",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "Text to replace it with.",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete",
            "description": "Delete a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list",
            "description": (
                "List the entries of a directory (directories end with '/')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Directory path. Defaults to the current directory."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute",
            "description": (
                "Run a shell command and return its stdout, stderr, and exit code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]


# --------------------------------------------------------------------------- #
# Dispatch.
# --------------------------------------------------------------------------- #

# Map each tool name to its implementation. Kept right next to TOOLS so adding a
# tool means touching exactly these two places. Handlers take keyword arguments
# (matching their JSON schema) and return a string.
_HANDLERS: dict[str, Callable[..., str]] = {
    "read": _read,
    "write": _write,
    "update": _update,
    "delete": _delete,
    "list": _list,
    "execute": _execute,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Run the named tool with the given arguments, returning a string result.

    Any failure (unknown tool, bad arguments, filesystem error, ...) is turned
    into an error string instead of raising, so the agent loop keeps going and
    the model can decide how to recover.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'"
    try:
        return handler(**arguments)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the model
        return f"Error: {type(exc).__name__}: {exc}"
