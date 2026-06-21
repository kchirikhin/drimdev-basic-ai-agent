#!/usr/bin/env bash
#
# Run the agent confined to a SINGLE writable directory using bubblewrap
# (the sandbox engine behind Flatpak). Inside the sandbox:
#   - the system (/usr, /bin, /lib, /etc, ...) is mounted READ-ONLY,
#   - the rest of your home is hidden behind a tmpfs,
#   - the Python venv and the agent's source are bound READ-ONLY,
#   - ONLY the sandbox directory is writable.
# So `execute`, `write`, `delete`, etc. physically cannot touch anything else.
# Network stays up so the agent can still reach the model (e.g. Ollama on
# localhost). This is an OS-level guard and does NOT depend on the agent's own
# (later) permission system.
#
# Usage:
#   ./run-sandboxed.sh [SANDBOX_DIR]      # default: ./sandbox
#
# Model/endpoint are taken from the environment (same vars as normal), e.g.:
#   OPENAI_MODEL=qwen2.5:7b-instruct ./run-sandboxed.sh ~/agent-work
#
set -euo pipefail

if ! command -v bwrap >/dev/null 2>&1; then
    echo "error: bubblewrap (bwrap) is not installed. Try: sudo apt install bubblewrap" >&2
    exit 1
fi

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX="${1:-$PROJECT/sandbox}"
mkdir -p "$SANDBOX"
SANDBOX="$(realpath "$SANDBOX")"

VENV="$(cd "$PROJECT" && poetry env info --path)"

# Bind the core system read-only. /lib64 only exists on some systems.
binds=(
    --ro-bind /usr /usr
    --ro-bind /bin /bin
    --ro-bind /lib /lib
    --ro-bind /etc /etc
    --proc /proc
    --dev /dev
)
[ -e /lib64 ] && binds+=(--ro-bind /lib64 /lib64)
[ -e /sbin ] && binds+=(--ro-bind /sbin /sbin)

echo "Sandbox (only writable directory): $SANDBOX"

exec bwrap \
    "${binds[@]}" \
    --tmpfs /tmp \
    --tmpfs /home \
    --ro-bind "$VENV" "$VENV" \
    --ro-bind "$PROJECT" "$PROJECT" \
    --bind "$SANDBOX" "$SANDBOX" \
    --chdir "$SANDBOX" \
    --unshare-all --share-net \
    --die-with-parent \
    --setenv PYTHONPATH "$PROJECT" \
    --setenv HOME "$SANDBOX" \
    --setenv OPENAI_BASE_URL "${OPENAI_BASE_URL:-http://localhost:11434/v1}" \
    --setenv OPENAI_API_KEY "${OPENAI_API_KEY:-ollama}" \
    --setenv OPENAI_MODEL "${OPENAI_MODEL:-qwen2.5:7b-instruct}" \
    "$VENV/bin/python" -m agent.cli
