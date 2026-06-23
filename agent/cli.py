"""Interactive terminal REPL for the agent.

Reads a line, shows a spinner while the model thinks, prints the reply, repeats.
A grey trace of each tool call makes the agentic loop visible.
"""

import itertools
import json
import threading
import time

from agent import context
from agent.config import CONTEXT_WINDOW, OPENAI_BASE_URL, OPENAI_MODEL
from agent.loop import Agent

GREEN = "\033[32m"
RED = "\033[31m"
GREY = "\033[90m"
RESET = "\033[0m"

CLEAR_LINE = "\r\033[K"  # carriage return + clear to end of line
CONTEXT_COMMANDS = {"context", "/context"}
EXIT_COMMANDS = {"exit", "quit", "q"}


def spinner(stop_event: threading.Event) -> None:
    """Animate a 'thinking' indicator until stop_event is set."""
    for frame in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        if stop_event.is_set():
            break
        print(f"\r{GREY}{frame} thinking...{RESET}", end="", flush=True)
        time.sleep(0.1)
    print(CLEAR_LINE, end="", flush=True)  # clear the spinner line


def print_tool_event(name: str, arguments: dict, result: str) -> None:
    """Show one tool call + a short result summary in grey."""
    args = json.dumps(arguments, ensure_ascii=False)
    summary = " ".join(result.split())  # collapse whitespace to one line
    if len(summary) > 80:
        summary = summary[:77] + "..."
    # Clear the spinner's current line first so the trace stays readable.
    print(f"{CLEAR_LINE}{GREY}⚙ {name}({args}) → {summary}{RESET}", flush=True)


def main() -> None:
    agent = Agent()

    print(f"{GREY}Basic AI Agent — model: {OPENAI_MODEL} @ {OPENAI_BASE_URL}{RESET}")
    if agent.agents_md_path is not None:
        print(f"{GREY}Loaded project instructions from {agent.agents_md_path}{RESET}")
    if agent.skills:
        print(f"{GREY}Available skills: {', '.join(agent.skills.names)}{RESET}")
    print(f"{GREY}Type 'context' for context usage, 'exit' to quit.{RESET}\n")

    while True:
        try:
            user_input = input(f"{GREEN}You: {RESET}")
        except (EOFError, KeyboardInterrupt):
            print()  # newline so the shell prompt starts cleanly
            break

        command = user_input.strip().lower()
        if command in EXIT_COMMANDS:
            break
        if command in CONTEXT_COMMANDS:
            summary = context.summarize_messages(agent.messages)
            print(f"{GREY}{context.format_summary(summary, CONTEXT_WINDOW)}{RESET}\n")
            continue
        if not user_input.strip():
            continue

        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
        spinner_thread.start()
        try:
            reply = agent.chat(user_input, on_tool_event=print_tool_event)
        finally:
            stop_event.set()
            spinner_thread.join()

        print(f"{RED}Agent:{RESET} {reply}\n")

    print(f"{GREY}Bye!{RESET}")


if __name__ == "__main__":
    main()
