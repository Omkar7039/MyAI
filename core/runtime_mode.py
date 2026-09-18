from __future__ import annotations

from dataclasses import dataclass

from core.runtime_consistency import RuntimeConsistencyReport
from core.runtime_diagnostics import RuntimeDiagnostics


@dataclass(frozen=True)
class RuntimeMode:
    mode: str
    accept_tasks: bool
    learning_enabled: bool
    reason: str


class RuntimeModeEvaluator:
    """
    Determine the safest operational mode from current runtime evidence.

    This evaluator is read-only. It never changes state, performs recovery,
    or shuts down the process.
    """

    NORMAL = "normal"
    DEGRADED = "degraded"
    RECOVERY = "recovery"
    STOPPED = "stopped"

    def evaluate(
        self,
        diagnostics: RuntimeDiagnostics,
        consistency: RuntimeConsistencyReport,
    ) -> RuntimeMode:
        if not diagnostics.runtime_state_available:
            return RuntimeMode(
                mode=self.STOPPED,
                accept_tasks=False,
                learning_enabled=False,
                reason="runtime state is unavailable",
            )

        if not consistency.consistent:
            return RuntimeMode(
                mode=self.RECOVERY,
                accept_tasks=False,
                learning_enabled=False,
                reason=(
                    "runtime state consistency checks failed: "
                    + "; ".join(consistency.issues)
                ),
            )

        if not diagnostics.learning_state_available:
            return RuntimeMode(
                mode=self.DEGRADED,
                accept_tasks=True,
                learning_enabled=False,
                reason="learning state is unavailable",
            )

        if not diagnostics.healthy:
            return RuntimeMode(
                mode=self.DEGRADED,
                accept_tasks=True,
                learning_enabled=False,
                reason=(
                    "runtime diagnostics reported recoverable issues"
                ),
            )

        return RuntimeMode(
            mode=self.NORMAL,
            accept_tasks=True,
            learning_enabled=True,
            reason="runtime is healthy and consistent",
        )
