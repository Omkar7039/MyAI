from __future__ import annotations

from dataclasses import dataclass

from core.runtime_state import RuntimeStateStore
from experience.persistent_learning_state import PersistentLearningState
from core.state_recovery import RuntimeStateRecovery


@dataclass(frozen=True)
class RuntimeDiagnostics:
    runtime_status: str | None
    clean_shutdown: bool | None
    last_exit_code: int | None
    runtime_schema_version: int
    active_strategy_count: int
    active_strategies: tuple[str, ...]
    rollback_available: tuple[str, ...]
    runtime_state_available: bool
    learning_state_available: bool
    healthy: bool
    issues: tuple[str, ...]


class RuntimeDiagnosticsChecker:
    """
    Read-only diagnostics for MyAI runtime and governed learning state.
    """

    def __init__(
        self,
        *,
        runtime_store: RuntimeStateStore | None = None,
        learning_state: PersistentLearningState | None = None,
    ):
        self.runtime_store = (
            runtime_store or RuntimeStateStore()
        )
        self.learning_state = (
            learning_state
            or PersistentLearningState(self.runtime_store)
        )

        self.recovery = RuntimeStateRecovery(
            runtime_store=self.runtime_store,
        )

    def recover_learning_state(
        self,
        error: Exception,
    ):
        return self.recovery.recover_learning_state(
            state=self.learning_state,
            error=error,
        )

    def recover_runtime_value(
        self,
        key: str,
        error: Exception,
    ):
        return self.recovery.recover_runtime_value(
            key=key,
            error=error,
        )

    def check(self) -> RuntimeDiagnostics:
        issues: list[str] = []

        runtime_state_available = False
        learning_state_available = False

        try:
            runtime_status = self.runtime_store.value(
                "runtime.status"
            )
            clean_raw = self.runtime_store.value(
                "runtime.clean_shutdown"
            )
            exit_raw = self.runtime_store.value(
                "runtime.last_exit_code"
            )

            runtime_schema_version = (
                self.runtime_store.schema_version()
            )

            runtime_state_available = True

        except Exception as exc:
            runtime_status = None
            clean_raw = None
            exit_raw = None
            runtime_schema_version = 0
            issues.append(
                f"runtime state unavailable: {exc}"
            )

        clean_shutdown = None

        if clean_raw in {"true", "false"}:
            clean_shutdown = (
                clean_raw == "true"
            )

        last_exit_code = None

        if exit_raw not in {None, ""}:
            try:
                last_exit_code = int(exit_raw)
            except (TypeError, ValueError):
                issues.append(
                    "invalid persisted runtime exit code"
                )

        try:
            changes, history = (
                self.learning_state.load_with_history()
            )

            learning_state_available = True

            active_strategies = tuple(
                change.strategy
                for change in changes
            )

            rollback_available = tuple(
                sorted(
                    strategy
                    for strategy, entries in history.items()
                    if entries
                )
            )

        except Exception as exc:
            active_strategies = ()
            rollback_available = ()
            issues.append(
                f"learning state unavailable: {exc}"
            )

        if not runtime_state_available:
            healthy = False
        elif not learning_state_available:
            healthy = False
        elif issues:
            healthy = False
        else:
            healthy = True

        return RuntimeDiagnostics(
            runtime_status=runtime_status,
            clean_shutdown=clean_shutdown,
            last_exit_code=last_exit_code,
            runtime_schema_version=runtime_schema_version,
            active_strategy_count=len(active_strategies),
            active_strategies=active_strategies,
            rollback_available=rollback_available,
            runtime_state_available=runtime_state_available,
            learning_state_available=learning_state_available,
            healthy=healthy,
            issues=tuple(issues),
        )
