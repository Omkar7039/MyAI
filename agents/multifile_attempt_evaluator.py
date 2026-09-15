from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MultiFileAttemptEvaluation:
    retryable: bool
    severity: str
    reason: str


class MultiFileAttemptEvaluator:
    def evaluate(self, result) -> MultiFileAttemptEvaluation:
        if result.get("success", False):
            return MultiFileAttemptEvaluation(
                retryable=False,
                severity="none",
                reason="Repair attempt succeeded.",
            )

        stage = str(
            result.get("stage", "unknown")
        ).lower()

        errors = tuple(
            str(error)
            for error in result.get("errors", [])
        )

        rolled_back = bool(
            result.get("rolled_back", False)
        )

        if stage == "planning":
            return MultiFileAttemptEvaluation(
                retryable=True,
                severity="high",
                reason="Planning failed; a new repair plan is required.",
            )

        if stage == "validation":
            return MultiFileAttemptEvaluation(
                retryable=True,
                severity="high",
                reason="Patch validation failed; the proposed patch is unsafe or invalid.",
            )

        if stage == "post_apply_verification":
            reason = (
                "Post-apply verification failed; the patch was rolled back "
                "and must be reconsidered."
                if rolled_back
                else
                "Post-apply verification failed; the patch must be reconsidered."
            )

            return MultiFileAttemptEvaluation(
                retryable=True,
                severity="high",
                reason=reason,
            )

        if rolled_back:
            return MultiFileAttemptEvaluation(
                retryable=True,
                severity="high",
                reason="Repair was rolled back after verification failure.",
            )

        if errors:
            return MultiFileAttemptEvaluation(
                retryable=True,
                severity="medium",
                reason="Repair attempt failed with reported errors.",
            )

        return MultiFileAttemptEvaluation(
            retryable=False,
            severity="unknown",
            reason="Repair failed without enough evidence to safely retry.",
        )
