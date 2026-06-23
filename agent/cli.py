"""Interactive terminal REPL for the agent.

Reads a line, shows a spinner while the model thinks, prints the reply, repeats.
A grey trace of each tool call makes the agentic loop visible.
"""

import itertools
import json
import threading
import time

from rich.console import Console
from rich.markdown import Markdown

from agent import context
from agent.config import CONTEXT_WINDOW, OPENAI_BASE_URL, OPENAI_MODEL
from agent.loop import Agent
from agent.permissions import ApprovalCallback

# Renders the agent's Markdown replies (headings, lists, syntax-highlighted code
# blocks). Auto-degrades to plain text when output isn't a terminal.
console = Console()

GREEN = "\033[32m"
RED = "\033[31m"
GREY = "\033[90m"
YELLOW = "\033[33m"
RESET = "\033[0m"

CLEAR_LINE = "\r\033[K"  # carriage return + clear to end of line
CONTEXT_COMMANDS = {"context", "/context"}
EXIT_COMMANDS = {"exit", "quit", "q"}


class Spinner:
    """A 'thinking…' indicator on a background thread that can be paused.

    Pausing matters because tool approval prompts need the terminal: we stop
    animating and clear the line so the prompt and the user's typing stay clean.
    """

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        print(CLEAR_LINE, end="", flush=True)

    def pause(self) -> None:
        self._paused.set()
        time.sleep(0.12)  # let any in-flight frame finish before clearing
        print(CLEAR_LINE, end="", flush=True)

    def resume(self) -> None:
        self._paused.clear()

    def _run(self) -> None:
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            if self._paused.is_set():
                time.sleep(0.05)
                continue
            print(f"\r{GREY}{frame} thinking...{RESET}", end="", flush=True)
            time.sleep(0.1)


def print_tool_event(name: str, arguments: dict, result: str) -> None:
    """Show one tool call + a short result summary in grey."""
    args = json.dumps(arguments, ensure_ascii=False)
    summary = " ".join(result.split())  # collapse whitespace to one line
    if len(summary) > 80:
        summary = summary[:77] + "..."
    # Clear the spinner's current line first so the trace stays readable.
    print(f"{CLEAR_LINE}{GREY}⚙ {name}({args}) → {summary}{RESET}", flush=True)


def make_confirmer(spinner: Spinner) -> ApprovalCallback:
    """Build an approve(name, arguments) callback that prompts the user.

    Remembers tools the user chose to 'always' allow, so it stops asking for
    them this session. The spinner is paused around the prompt.
    """
    always_allowed: set[str] = set()

    def confirm(name: str, arguments: dict) -> bool:
        if name in always_allowed:
            return True
        spinner.pause()
        try:
            args = json.dumps(arguments, ensure_ascii=False)
            if len(args) > 120:
                args = args[:117] + "..."
            answer = (
                input(f"{YELLOW}Allow {name}({args})? [y]es / [n]o / [a]lways: {RESET}")
                .strip()
                .lower()
            )
        except EOFError:  # no input available -> deny, the safe default
            answer = "n"
        finally:
            spinner.resume()
        if answer in ("a", "always"):
            always_allowed.add(name)
            return True
        return answer in ("y", "yes")

    return confirm


def main() -> None:
    agent = Agent()
    spinner = Spinner()
    confirm = make_confirmer(spinner)

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

        spinner.start()
        try:
            reply = agent.chat(
                user_input, on_tool_event=print_tool_event, approve=confirm
            )
        finally:
            spinner.stop()

        print(f"{RED}Agent:{RESET}")
        console.print(Markdown(reply))
        print()

    print(f"{GREY}Bye!{RESET}")


if __name__ == "__main__":
    main()
