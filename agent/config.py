"""Environment-based configuration.

Defaults target a local Ollama server (see SPEC.md). `OPENAI_BASE_URL` and
`OPENAI_API_KEY` are the standard names the openai SDK recognizes; `OPENAI_MODEL`
is our own convention.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "system_prompt.txt"

# OpenAI-compatible backend configuration
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "qwen2.5-coder:7b")

# Model context window, used only to show a percentage in the `context` command.
CONTEXT_WINDOW = int(os.getenv("OPENAI_CONTEXT_WINDOW", "32768"))
