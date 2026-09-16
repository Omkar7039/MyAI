import os
import signal
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

from core.orchestrator import Orchestrator
from core.runtime_lifecycle import RuntimeLifecycle
from core.runtime_services import RuntimeServices


def create_bindings():
    bindings = KeyBindings()

    @bindings.add("enter")
    def submit(event):
        event.current_buffer.validate_and_handle()

    return bindings


def handle_runtime_command(command, services):
    """
    Handle MyAI runtime/maintenance commands.

    Returns True when the command was handled, otherwise False.
    """
    if command == "/status":
        snapshot = services.status_snapshot()

        print()
        print(f"Runtime status: {snapshot.status}")
        print(f"Healthy: {snapshot.healthy}")
        print(
            "Active strategies: "
            f"{snapshot.active_strategies or 'none'}"
        )
        print(
            "Rollback available: "
            f"{snapshot.rollback_available or 'none'}"
        )
        print(
            "Clean shutdown: "
            f"{snapshot.clean_shutdown}"
        )
        print(
            "Last exit code: "
            f"{snapshot.last_exit_code}"
        )

        if snapshot.issues:
            for issue in snapshot.issues:
                print(f"Diagnostic: {issue}")

        print()
        return True

    if command == "/retention":
        report = services.preview_learning_retention()

        print()
        print("Learning retention preview:")
        print(f"Strategies scanned: {report.scanned_strategies}")
        print(f"Entries retained: {report.retained_entries}")
        print(f"Entries to prune: {report.pruned_entries}")
        print()

        return True

    if command == "/retention apply":
        report = services.apply_learning_retention()

        print()
        print("Learning retention applied:")
        print(f"Strategies scanned: {report.scanned_strategies}")
        print(f"Entries retained: {report.retained_entries}")
        print(f"Entries pruned: {report.pruned_entries}")
        print()

        return True

    return False



def main():
    lifecycle = RuntimeLifecycle()
    services = RuntimeServices.create(lifecycle.store)

    exit_code_recovery = (
        services.recover_runtime_exit_code_if_needed()
    )

    if exit_code_recovery is not None and exit_code_recovery.recovered:
        print(
            "[MyAI] Invalid persisted runtime exit code was "
            "quarantined."
        )

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

    recovery = services.recover_learning_state_if_needed()

    if recovery is not None and recovery.recovered:
        print(
            "[MyAI] Persisted learning state was malformed and "
            "was safely quarantined."
        )

    # Keep persisted governed-learning rollback history bounded.
    services.apply_learning_retention()

    readiness = services.check_readiness()

    if not readiness.ready:
        print("[MyAI] Runtime readiness check failed.")

        for issue in readiness.diagnostics.issues:
            print(f"[MyAI] Runtime diagnostic: {issue}")

        lifecycle.shutdown(exit_code=1)
        raise SystemExit(1)

    lifecycle.mark_ready()

    print()
    print("MyAI is ready.")
    print()
    print("Enter = send")
    print("Paste multiline code + Enter = send")
    print("Commands:")
    print("  /reset  - clear conversation")
    print("  /status - show runtime status")
    print("  /retention - preview learning retention")
    print("  /retention apply - apply learning retention")
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

                if handle_runtime_command(command, services):
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
