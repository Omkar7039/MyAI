import os
import signal
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

from core.orchestrator import Orchestrator
from core.runtime_lifecycle import RuntimeLifecycle


def create_bindings():
    bindings = KeyBindings()

    @bindings.add("enter")
    def submit(event):
        event.current_buffer.validate_and_handle()

    return bindings


def main():
    lifecycle = RuntimeLifecycle()

    startup = lifecycle.startup()

    if not startup.previous_clean_shutdown:
        print(
            "[MyAI] Previous runtime did not end with a "
            "clean shutdown."
        )

    stopping = False

    def stop_myai(signum=None, frame=None):
        nonlocal stopping

        if stopping:
            return

        stopping = True
        print("\n\nStopping MyAI...")

        try:
            lifecycle.shutdown(exit_code=130)
        finally:
            raise SystemExit(130)

    signal.signal(signal.SIGINT, stop_myai)

    print("Starting MyAI...")
    ai = Orchestrator()

    lifecycle.mark_ready()

    print()
    print("MyAI is ready.")
    print()
    print("Enter = send")
    print("Paste multiline code + Enter = send")
    print("Commands:")
    print("  /reset  - clear conversation")
    print("  /exit   - exit MyAI")
    print("  Ctrl+C  - emergency stop")
    print()

    session = PromptSession(
        key_bindings=create_bindings(),
        multiline=True,
        enable_history_search=True,
    )

    try:
        while True:
            try:
                user_input = session.prompt("You: ")

                user_input = user_input.strip()

                if not user_input:
                    continue

                command = user_input.lower()

                if command in {"/exit", "exit", "quit", "q"}:
                    print("Goodbye.")
                    lifecycle.shutdown(exit_code=0)
                    break

                if command == "/reset":
                    ai.context.clear()
                    print("Conversation memory cleared.")
                    continue

                print("\nAI:")

                response = ai.handle(user_input)

                print(response)
                print()

            except EOFError:
                print("\nStopping MyAI...")
                lifecycle.shutdown(exit_code=0)
                break

            except KeyboardInterrupt:
                stop_myai()

            except Exception as exc:
                print(f"\nMyAI error: {exc}")

    except SystemExit:
        raise
    except Exception:
        lifecycle.shutdown(exit_code=1)
        raise


if __name__ == "__main__":
    main()
