"""Interactive terminal REPL for the agent.

Reads a line, shows a spinner while the model thinks, prints the reply, repeats.
"""

import itertools
import threading
import time

from agent.config import OPENAI_BASE_URL, OPENAI_MODEL
from agent.loop import Agent

GREEN = "\033[32m"
RED = "\033[31m"
GREY = "\033[90m"
RESET = "\033[0m"

EXIT_COMMANDS = {"exit", "quit", "q"}


def spinner(stop_event: threading.Event) -> None:
    """Animate a 'thinking' indicator until stop_event is set."""
    for frame in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        if stop_event.is_set():
            break
        print(f"\r{GREY}{frame} thinking...{RESET}", end="", flush=True)
        time.sleep(0.1)
    print("\r\033[K", end="", flush=True)  # clear the spinner line


def main() -> None:
    agent = Agent()

    print(f"{GREY}Basic AI Agent — model: {OPENAI_MODEL} @ {OPENAI_BASE_URL}{RESET}")
    print(f"{GREY}Type 'exit' or press Ctrl-C to quit.{RESET}\n")

    while True:
        try:
            user_input = input(f"{GREEN}You: {RESET}")
        except (EOFError, KeyboardInterrupt):
            print()  # newline so the shell prompt starts cleanly
            break

        if user_input.strip().lower() in EXIT_COMMANDS:
            break
        if not user_input.strip():
            continue

        stop_event = threading.Event()
        spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
        spinner_thread.start()
        try:
            reply = agent.chat(user_input)
        finally:
            stop_event.set()
            spinner_thread.join()

        print(f"{RED}Agent:{RESET} {reply}\n")

    print(f"{GREY}Bye!{RESET}")


if __name__ == "__main__":
    main()
