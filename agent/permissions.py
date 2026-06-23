"""Permissions — confirmation before side-effecting tools (Step 6).

Some tools change the world: writing or deleting files, running shell commands.
Before such a tool runs, the agent asks for approval through a callback the host
(the CLI) supplies. This is the safety/control layer: the agent stays autonomous
but the human keeps a veto.

When no approval callback is provided (tests, programmatic use), nothing is
gated. The set below is the policy — add `update` here too if you want in-place
edits gated as well.
"""

from collections.abc import Callable

# Tools that require explicit user approval before they run.
TOOLS_REQUIRING_APPROVAL = {"write", "delete", "execute"}

# Returned to the model as the tool result when the user denies a call, so it can
# react (apologise, suggest an alternative) instead of silently failing.
DENIED_RESULT = "Error: the user denied permission to run this tool."

# Called as approve(name, arguments) -> True to allow, False to deny.
ApprovalCallback = Callable[[str, dict], bool]
