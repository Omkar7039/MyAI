from __future__ import annotations

from dataclasses import dataclass

from core.runtime_failure import RuntimeFailureClassification


@dataclass(frozen=True)
class RuntimeRecoveryDecision:
    action: str
    safe_to_continue: bool
    reason: str


class RuntimeRecoveryDecisionEngine:
    """
    Decide what should happen after a runtime failure is classified.

    This class is intentionally pure: it never retries, mutates state,
    performs recovery, or shuts down the process.
    """

    CONTINUE = "continue"
    RECOVER = "recover"
    RETRY = "retry"
    STOP = "stop"

    def decide(
        self,
        classification: RuntimeFailureClassification,
    ) -> RuntimeRecoveryDecision:
        category = classification.category

        if category == "none":
            return RuntimeRecoveryDecision(
                action=self.CONTINUE,
                safe_to_continue=True,
                reason="no runtime failure was detected",
            )

        if category == "timeout":
            return RuntimeRecoveryDecision(
                action=self.RETRY,
                safe_to_continue=False,
                reason="timeout is retryable before state recovery is needed",
            )

        if classification.recoverable:
            return RuntimeRecoveryDecision(
                action=self.RECOVER,
                safe_to_continue=False,
                reason=(
                    f"{category} failure is recoverable and "
                    "requires recovery before continuing"
                ),
            )

        if classification.retryable:
            return RuntimeRecoveryDecision(
                action=self.RETRY,
                safe_to_continue=False,
                reason=(
                    f"{category} failure is retryable"
                ),
            )

        return RuntimeRecoveryDecision(
            action=self.STOP,
            safe_to_continue=False,
            reason=(
                f"{category} failure is not automatically "
                "recoverable or retryable"
            ),
        )
