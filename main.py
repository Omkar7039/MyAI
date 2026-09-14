
import os
import signal

from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings

from core.orchestrator import Orchestrator


def stop_myai(signum, frame):
    print("\n\nStopping MyAI...")
    os._exit(130)


def create_bindings():
    bindings = KeyBindings()

    @bindings.add("enter")
    def submit(event):
        event.current_buffer.validate_and_handle()

    return bindings


def main():
    signal.signal(signal.SIGINT, stop_myai)

    print("Starting MyAI...")
    ai = Orchestrator()

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

    while True:
        try:
            user_input = session.prompt("You: ")

            user_input = user_input.strip()

            if not user_input:
                continue

            command = user_input.lower()

            if command in {"/exit", "exit", "quit", "q"}:
                print("Goodbye.")
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
            break

        except KeyboardInterrupt:
            print("\nStopping MyAI...")
            break

        except Exception as exc:
            print(f"\nMyAI error: {exc}")


if __name__ == "__main__":
    main()
