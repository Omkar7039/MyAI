from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MultiFileRepairAttempt:
    attempt: int
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
    ):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.executor = executor
        self.max_attempts = max_attempts

    def repair(self, request, project_root):
        attempts = []

        for attempt_number in range(1, self.max_attempts + 1):
            result = self.executor.execute(
                request=request,
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

        return AutonomousMultiFileRepairResult(
            success=False,
            attempts=tuple(attempts),
            stopped_safely=True,
            reason="Maximum autonomous multi-file repair attempts reached.",
        )
