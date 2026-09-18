from __future__ import annotations

from dataclasses import dataclass

from core.runtime_diagnostics import RuntimeDiagnostics
from core.task_supervisor import TaskSupervisor

from core.runtime_diagnostics import RuntimeDiagnosticsChecker
from core.runtime_state import RuntimeStateStore
from experience.learning_state_retention import (
    LearningStateRetentionManager,
)
from experience.persistent_learning_state import PersistentLearningState
from core.runtime_recovery_controller import RuntimeRecoveryController
from core.supervised_task_runner import SupervisedTaskRunner


@dataclass(frozen=True)
class RuntimeStatusSnapshot:
    status: str | None
    healthy: bool
    active_strategy_count: int
    active_strategies: tuple[str, ...]
    rollback_available: tuple[str, ...]
    clean_shutdown: bool | None
    last_exit_code: int | None
    issues: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeReadiness:
    ready: bool
    diagnostics: RuntimeDiagnostics


@dataclass(frozen=True)
class RuntimeServices:
    store: RuntimeStateStore
    learning_state: PersistentLearningState
    diagnostics: RuntimeDiagnosticsChecker
    retention: LearningStateRetentionManager
    task_supervisor: TaskSupervisor
    recovery_controller: RuntimeRecoveryController
    task_runner: SupervisedTaskRunner

    def status_snapshot(self) -> RuntimeStatusSnapshot:
        """
        Return a compact, read-only operational runtime snapshot.
        """
        diagnostics = self.diagnostics.check()

        return RuntimeStatusSnapshot(
            status=diagnostics.runtime_status,
            healthy=diagnostics.healthy,
            active_strategy_count=diagnostics.active_strategy_count,
            active_strategies=diagnostics.active_strategies,
            rollback_available=diagnostics.rollback_available,
            clean_shutdown=diagnostics.clean_shutdown,
            last_exit_code=diagnostics.last_exit_code,
            issues=diagnostics.issues,
        )

    def check_readiness(self) -> RuntimeReadiness:
        """
        Return a read-only readiness decision based on current diagnostics.

        Readiness does not mutate runtime or learning state.
        """
        diagnostics = self.diagnostics.check()

        return RuntimeReadiness(
            ready=diagnostics.healthy,
            diagnostics=diagnostics,
        )

    def preview_learning_retention(self):
        """
        Inspect rollback-history retention without modifying state.
        """
        return self.retention.run(apply=False)

    def apply_learning_retention(self):
        """
        Apply the configured rollback-history retention policy.
        """
        return self.retention.run(apply=True)

    def recover_runtime_exit_code_if_needed(self):
        """
        Validate the persisted runtime exit code before lifecycle startup.

        RuntimeLifecycle.startup() intentionally clears the previous exit
        code, so malformed persisted values must be handled first.
        """
        key = "runtime.last_exit_code"
        raw = self.store.value(key)

        if raw in {None, ""}:
            return None

        try:
            int(raw)
        except (TypeError, ValueError) as exc:
            return self.diagnostics.recover_runtime_value(
                key,
                exc,
            )

        return None

    def recover_learning_state_if_needed(self):
        """
        Validate persisted learning state and recover it if malformed.

        Healthy persisted state is left untouched. Malformed state is
        quarantined through the existing recovery service.
        """
        try:
            self.learning_state.load_with_history()
        except Exception as exc:
            return self.diagnostics.recover_learning_state(exc)

        return None

    @classmethod
    def create(
        cls,
        store: RuntimeStateStore | None = None,
        *,
        max_rollback_entries: int = 10,
    ) -> "RuntimeServices":
        runtime_store = store or RuntimeStateStore()
        learning_state = PersistentLearningState(runtime_store)
        task_supervisor = TaskSupervisor()
        recovery_controller = RuntimeRecoveryController()

        return cls(
            store=runtime_store,
            learning_state=learning_state,
            diagnostics=RuntimeDiagnosticsChecker(
                runtime_store=runtime_store,
                learning_state=learning_state,
            ),
            retention=LearningStateRetentionManager(
                learning_state,
                max_rollback_entries=max_rollback_entries,
            ),
            task_supervisor=task_supervisor,
            recovery_controller=recovery_controller,
            task_runner=SupervisedTaskRunner(
                supervisor=task_supervisor,
                recovery_controller=recovery_controller,
            ),
        )
