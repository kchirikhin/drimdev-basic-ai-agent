"""Thin factory for the OpenAI-compatible client.

Kept separate so later steps (tools, subagents, ...) can reuse the same client.
"""

from openai import OpenAI

from agent.config import OPENAI_API_KEY, OPENAI_BASE_URL


def get_client() -> OpenAI:
    """Create an OpenAI client pointed at the configured backend."""
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
