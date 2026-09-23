from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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
from core.persistent_task_supervisor import PersistentTaskSupervisor
from core.task_queue import TaskQueue
from core.task_queue_coordinator import TaskQueueCoordinator
from core.task_resume import TaskResumeManager
from core.task_resume_report import TaskResumeReport, TaskResumeReportStore
from core.task_queue_retention import TaskQueueRetentionManager


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
    resume_total_unfinished: int = 0
    resume_requeued: int = 0
    resume_reconciled: int = 0
    resume_failed: int = 0


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
    task_queue_coordinator: TaskQueueCoordinator
    task_resume_manager: TaskResumeManager
    task_resume_reports: TaskResumeReportStore
    task_queue_retention: TaskQueueRetentionManager

    def status_snapshot(self) -> RuntimeStatusSnapshot:
        """
        Return a compact, read-only operational runtime snapshot.
        """
        diagnostics = self.diagnostics.check()

        report = (
            self.task_resume_reports.load()
            if self.task_resume_reports is not None
            else None
        )

        return RuntimeStatusSnapshot(
            status=diagnostics.runtime_status,
            healthy=diagnostics.healthy,
            active_strategy_count=diagnostics.active_strategy_count,
            active_strategies=diagnostics.active_strategies,
            rollback_available=diagnostics.rollback_available,
            clean_shutdown=diagnostics.clean_shutdown,
            last_exit_code=diagnostics.last_exit_code,
            issues=diagnostics.issues,
            resume_total_unfinished=(
                report.total_unfinished if report is not None else 0
            ),
            resume_requeued=(
                report.requeued if report is not None else 0
            ),
            resume_reconciled=(
                report.reconciled if report is not None else 0
            ),
            resume_failed=(
                report.failed if report is not None else 0
            ),
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

    def preview_task_queue_retention(self):
        """Inspect task-queue retention without modifying queue state."""
        return self.task_queue_retention.run(apply=False)

    def apply_task_queue_retention(self):
        """Apply task-queue terminal-history retention."""
        return self.task_queue_retention.run(apply=True)

    def resume_report(self) -> TaskResumeReport | None:
        """Return the last persisted task-resume report."""
        if self.task_resume_reports is None:
            return None

        return self.task_resume_reports.load()

    def clear_resume_report(self) -> None:
        """Clear the persisted task-resume report."""
        if self.task_resume_reports is None:
            return

        self.task_resume_reports.clear()

    def get_queued(self, task_id: str):
        """Return a queued task by ID."""
        return self.task_queue_coordinator.get_queued(task_id)

    def get_supervised(self, task_id: str):
        """Return supervised task state by ID."""
        return self.task_queue_coordinator.get_supervised(task_id)

    def recover_tasks_if_needed(
        self,
        *,
        previous_clean_shutdown: bool,
    ) -> TaskResumeReport | None:
        """
        Reconcile unfinished durable tasks only after an unclean shutdown.

        Clean restarts leave task state untouched.
        """
        if previous_clean_shutdown:
            return None

        if (
            self.task_resume_manager is None
            or self.task_resume_reports is None
        ):
            return None

        actions = self.task_resume_manager.recover_unfinished()

        if not actions:
            return None

        report = TaskResumeReport(
            recovered_at=datetime.now(timezone.utc).isoformat(),
            total_unfinished=len(actions),
            requeued=sum(action.action == "requeue" for action in actions),
            reconciled=sum(
                action.action == "reconcile"
                for action in actions
            ),
            failed=sum(action.action == "failed" for action in actions),
            actions=actions,
        )

        self.task_resume_reports.save(report)
        return report

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
        max_task_terminal_entries: int = 100,
    ) -> "RuntimeServices":
        runtime_store = store or RuntimeStateStore()
        learning_state = PersistentLearningState(runtime_store)
        task_supervisor = TaskSupervisor()
        recovery_controller = RuntimeRecoveryController()

        task_queue = TaskQueue(runtime_store)
        persistent_task_supervisor = PersistentTaskSupervisor(
            store=runtime_store,
        )
        task_queue_coordinator = TaskQueueCoordinator(
            queue=task_queue,
            supervisor=persistent_task_supervisor,
        )
        task_resume_manager = TaskResumeManager(
            task_queue_coordinator,
        )
        task_resume_reports = TaskResumeReportStore(
            runtime_store,
        )
        task_queue_retention = TaskQueueRetentionManager(
            task_queue,
            max_terminal_tasks=max_task_terminal_entries,
        )

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
            task_queue_coordinator=task_queue_coordinator,
            task_resume_manager=task_resume_manager,
            task_resume_reports=task_resume_reports,
            task_queue_retention=task_queue_retention,
        )
