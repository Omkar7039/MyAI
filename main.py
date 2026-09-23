import os
import signal
import sys
from uuid import uuid4

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
        print(
            "Last task resume: "
            f"unfinished={snapshot.resume_total_unfinished}, "
            f"requeued={snapshot.resume_requeued}, "
            f"reconciled={snapshot.resume_reconciled}, "
            f"failed={snapshot.resume_failed}"
        )

        if snapshot.issues:
            for issue in snapshot.issues:
                print(f"Diagnostic: {issue}")

        print()
        return True

    if command == "/task-retention":
        report = services.preview_task_queue_retention()

        print()
        print("Task queue retention preview:")
        print(
            "Terminal tasks: "
            f"{report.existing_terminal_tasks}"
        )
        print(
            "Terminal tasks retained: "
            f"{report.retained_terminal_tasks}"
        )
        print(
            "Terminal tasks to prune: "
            f"{report.pruned_terminal_tasks}"
        )
        print(
            "Active tasks preserved: "
            f"{report.active_tasks}"
        )
        print()

        return True

    if command == "/task-retention apply":
        report = services.apply_task_queue_retention()

        print()
        print("Task queue retention applied:")
        print(
            "Terminal tasks scanned: "
            f"{report.existing_terminal_tasks}"
        )
        print(
            "Terminal tasks retained: "
            f"{report.retained_terminal_tasks}"
        )
        print(
            "Terminal tasks pruned: "
            f"{report.pruned_terminal_tasks}"
        )
        print(
            "Active tasks preserved: "
            f"{report.active_tasks}"
        )
        print()

        return True

    if command == "/resume":
        report = services.resume_report()

        print()
        print("Last task resume report:")

        if report is None:
            print("No task resume report available.")
        else:
            print(f"Recovered at: {report.recovered_at}")
            print(f"Unfinished: {report.total_unfinished}")
            print(f"Requeued: {report.requeued}")
            print(f"Reconciled: {report.reconciled}")
            print(f"Failed: {report.failed}")

            if report.actions:
                print("Actions:")
                for action in report.actions:
                    print(
                        f"  {action.task_id}: "
                        f"{action.action} — {action.reason}"
                    )

        print()
        return True

    if command == "/resume clear":
        services.clear_resume_report()

        print()
        print("Task resume report cleared.")
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



def run_supervised_request(
    ai,
    services,
    user_input: str,
):
    """
    Execute one interactive request through the shared task supervisor.
    """
    task_id = f"interactive-{uuid4().hex}"

    result = services.task_runner.run(
        task_id=task_id,
        execute=lambda: ai.handle(user_input),
        fingerprint=f"request:{task_id}",
        max_task_retries=1,
    )

    if result.response is None:
        print(
            f"\n[MyAI] Task {result.task.task_id} "
            f"{result.task.status}: {result.task.reason}"
        )
        return result

    print(result.response)
    return result



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

    task_resume = services.recover_tasks_if_needed(
        previous_clean_shutdown=startup.previous_clean_shutdown,
    )

    if task_resume is not None:
        print(
            "[MyAI] Task resume recovery: "
            f"{task_resume.total_unfinished} unfinished, "
            f"{task_resume.requeued} requeued, "
            f"{task_resume.reconciled} reconciled, "
            f"{task_resume.failed} failed."
        )

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
    print("  /resume - show last task resume report")
    print("  /resume clear - clear task resume report")
    print("  /task-retention - preview task queue retention")
    print("  /task-retention apply - apply task queue retention")
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

                run_supervised_request(
                    ai,
                    services,
                    user_input,
                )

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
