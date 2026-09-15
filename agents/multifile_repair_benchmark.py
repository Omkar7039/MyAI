from __future__ import annotations

from dataclasses import dataclass

from agents.autonomous_multifile_improvement import (
    MultiFileRepairImprovementPlanner,
)
from agents.autonomous_multifile_repair import (
    AutonomousMultiFileRepair,
)
from agents.autonomous_multifile_retry import (
    AutonomousMultiFileRetryPlanner,
)
from agents.multifile_attempt_evaluator import (
    MultiFileAttemptEvaluator,
)
from agents.multifile_recovery import (
    MultiFileRecoveryManager,
)
from agents.multifile_regression_validator import (
    MultiFileRegressionValidator,
)
from agents.multifile_reverification import (
    MultiFileReverification,
)


@dataclass(frozen=True)
class MultiFileRepairBenchmarkResult:
    controller: float
    retry_context: float
    attempt_evaluation: float
    improvement: float
    reverification: float
    regression: float
    recovery: float
    overall: float


class MultiFileRepairBenchmark:
    def run(self) -> MultiFileRepairBenchmarkResult:
        values = {
            "controller": self._controller(),
            "retry_context": self._retry_context(),
            "attempt_evaluation": self._attempt_evaluation(),
            "improvement": self._improvement(),
            "reverification": self._reverification(),
            "regression": self._regression(),
            "recovery": self._recovery(),
        }

        return MultiFileRepairBenchmarkResult(
            **values,
            overall=sum(values.values()) / len(values),
        )

    def _controller(self):
        class Executor:
            def __init__(self):
                self.calls = 0

            def execute(self, request, project_root):
                self.calls += 1

                if self.calls == 1:
                    return {
                        "success": False,
                        "stage": "post_apply_verification",
                        "errors": ["verification failed"],
                        "rolled_back": True,
                    }

                return {
                    "success": True,
                    "stage": "complete",
                    "errors": [],
                    "rolled_back": False,
                }

        executor = Executor()

        result = AutonomousMultiFileRepair(
            executor,
            max_attempts=3,
        ).repair(
            request="Repair project",
            project_root="/tmp/project",
        )

        return 100.0 if (
            result.success
            and len(result.attempts) == 2
            and executor.calls == 2
        ) else 0.0

    def _retry_context(self):
        context = (
            AutonomousMultiFileRetryPlanner()
            .build_request
        )(
            "Repair project",
            __import__(
                "agents.autonomous_multifile_retry",
                fromlist=["RetryContext"],
            ).RetryContext(
                attempt=1,
                previous_stage="post_apply_verification",
                previous_errors=("verification failed",),
                previous_rolled_back=True,
            ),
        )

        return 100.0 if (
            "AUTONOMOUS RETRY CONTEXT:" in context
            and "verification failed" in context
        ) else 0.0

    def _attempt_evaluation(self):
        result = MultiFileAttemptEvaluator().evaluate(
            {
                "success": False,
                "stage": "post_apply_verification",
                "errors": ["verification failed"],
                "rolled_back": True,
            }
        )

        return 100.0 if (
            result.retryable
            and result.severity == "high"
        ) else 0.0

    def _improvement(self):
        improvement = (
            MultiFileRepairImprovementPlanner()
            .plan(
                {
                    "success": False,
                    "stage": "post_apply_verification",
                    "errors": ["verification failed"],
                    "rolled_back": True,
                }
            )
        )

        directive = (
            MultiFileRepairImprovementPlanner()
            .build_directive(improvement)
        )

        return 100.0 if (
            "Change the repair approach" in improvement.strategy
            and "AUTONOMOUS REPAIR IMPROVEMENT:" in directive
        ) else 0.0

    def _reverification(self):
        result = MultiFileReverification().verify(
            {
                "success": True,
                "stage": "complete",
                "errors": [],
                "rolled_back": False,
            }
        )

        return 100.0 if result.verified else 0.0

    def _regression(self):
        result = MultiFileRegressionValidator().validate(
            {
                "success": True,
                "checked_files": [
                    "a.py",
                    "b.py",
                ],
                "failed_files": [],
            },
            expected_files=["a.py", "b.py"],
        )

        return 100.0 if (
            result.verified
            and not result.failed_files
        ) else 0.0

    def _recovery(self):
        result = MultiFileRecoveryManager().evaluate(
            {
                "success": False,
                "rolled_back": True,
            }
        )

        return 100.0 if (
            result.safe_to_continue
            and result.rolled_back
        ) else 0.0
