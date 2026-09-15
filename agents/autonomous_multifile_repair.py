from __future__ import annotations

from dataclasses import dataclass

from agents.autonomous_multifile_retry import (
    AutonomousMultiFileRetryPlanner,
    RetryContext,
)


@dataclass(frozen=True)
class MultiFileRepairAttempt:
    attempt: int
    request: str
    success: bool
    stage: str
    errors: tuple[str, ...]
    rolled_back: bool


@dataclass(frozen=True)
class AutonomousMultiFileRepairResult:
    success: bool
    attempts: tuple[MultiFileRepairAttempt, ...]
    stopped_safely: bool
    reason: str


class AutonomousMultiFileRepair:
    def __init__(
        self,
        executor,
        max_attempts: int = 3,
        retry_planner: AutonomousMultiFileRetryPlanner | None = None,
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.executor = executor
        self.max_attempts = max_attempts
        self.retry_planner = (
            retry_planner or AutonomousMultiFileRetryPlanner()
        )

    def repair(self, request, project_root):
        attempts = []
        current_request = request

        for attempt_number in range(
            1,
            self.max_attempts + 1,
        ):
            result = self.executor.execute(
                request=current_request,
                project_root=project_root,
            )

            success = bool(
                result.get("success", False)
            )

            errors = tuple(
                str(error)
                for error in result.get("errors", [])
            )

            attempt = MultiFileRepairAttempt(
                attempt=attempt_number,
                request=current_request,
                success=success,
                stage=str(
                    result.get("stage", "unknown")
                ),
                errors=errors,
                rolled_back=bool(
                    result.get("rolled_back", False)
                ),
            )

            attempts.append(attempt)

            if success:
                return AutonomousMultiFileRepairResult(
                    success=True,
                    attempts=tuple(attempts),
                    stopped_safely=False,
                    reason="Multi-file repair verified successfully.",
                )

            if attempt_number >= self.max_attempts:
                break

            retry_context = RetryContext(
                attempt=attempt_number,
                previous_stage=attempt.stage,
                previous_errors=attempt.errors,
                previous_rolled_back=attempt.rolled_back,
            )

            current_request = self.retry_planner.build_request(
                request,
                retry_context,
            )

        return AutonomousMultiFileRepairResult(
            success=False,
            attempts=tuple(attempts),
            stopped_safely=True,
            reason="Maximum autonomous multi-file repair attempts reached.",
        )
