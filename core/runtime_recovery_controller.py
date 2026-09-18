from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.runtime_failure import (
    RuntimeFailureClassification,
    RuntimeFailureClassifier,
)
from core.runtime_recovery import (
    RuntimeRecoveryDecision,
    RuntimeRecoveryDecisionEngine,
)
from core.runtime_recovery_audit import RuntimeRecoveryAudit
from core.runtime_recovery_guard import (
    RecoveryGuardResult,
    RuntimeRecoveryGuard,
)
from core.runtime_recovery_throttle import (
    RecoveryThrottleResult,
    RuntimeRecoveryThrottle,
)


@dataclass(frozen=True)
class RuntimeRecoveryExecution:
    classification: RuntimeFailureClassification
    decision: RuntimeRecoveryDecision
    guard: RecoveryGuardResult | None
    throttle: RecoveryThrottleResult | None
    recovered: bool
    action: str
    reason: str


class RuntimeRecoveryController:
    """
    Coordinate runtime failure classification, recovery policy, safety
    controls, optional recovery execution, and auditing.
    """

    def __init__(
        self,
        *,
        classifier: RuntimeFailureClassifier | None = None,
        decision_engine: RuntimeRecoveryDecisionEngine | None = None,
        guard: RuntimeRecoveryGuard | None = None,
        throttle: RuntimeRecoveryThrottle | None = None,
        audit: RuntimeRecoveryAudit | None = None,
    ):
        self.classifier = (
            classifier or RuntimeFailureClassifier()
        )
        self.decision_engine = (
            decision_engine
            or RuntimeRecoveryDecisionEngine()
        )
        self.guard = (
            guard or RuntimeRecoveryGuard()
        )
        self.throttle = (
            throttle or RuntimeRecoveryThrottle()
        )
        self.audit = (
            audit or RuntimeRecoveryAudit()
        )

    def handle(
        self,
        *,
        fingerprint: str,
        error: Exception | None = None,
        timed_out: bool = False,
        stderr: str = "",
        message: str = "",
        runtime_failed: bool = False,
        recover: Callable[[], bool] | None = None,
    ) -> RuntimeRecoveryExecution:
        classification = self.classifier.classify(
            error,
            timed_out=timed_out,
            stderr=stderr,
            message=message,
            runtime_failed=runtime_failed,
        )

        decision = self.decision_engine.decide(
            classification
        )

        self.audit.record_decision(
            fingerprint=fingerprint,
            classification=classification,
            decision=decision,
        )

        if decision.action == "continue":
            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=None,
                throttle=None,
                recovered=False,
                action="continue",
                reason=decision.reason,
            )

        if decision.action == "retry":
            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=None,
                throttle=None,
                recovered=False,
                action="retry",
                reason=decision.reason,
            )

        if decision.action != "recover":
            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=None,
                throttle=None,
                recovered=False,
                action="stop",
                reason=decision.reason,
            )

        guard_result = self.guard.check(
            fingerprint
        )

        self.audit.record_guard(
            fingerprint=fingerprint,
            classification=classification,
            guard=guard_result,
        )

        if not guard_result.allowed:
            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=guard_result,
                throttle=None,
                recovered=False,
                action="stop",
                reason=guard_result.reason,
            )

        throttle_result = self.throttle.check(
            fingerprint
        )

        if not throttle_result.allowed:
            self.audit.record(
                fingerprint=fingerprint,
                category=classification.category,
                action="cooldown_block",
                allowed=False,
                attempts=guard_result.attempts,
                reason=throttle_result.reason,
            )

            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=guard_result,
                throttle=throttle_result,
                recovered=False,
                action="stop",
                reason=throttle_result.reason,
            )

        self.guard.record(fingerprint)
        self.throttle.record(fingerprint)

        if recover is None:
            self.audit.record(
                fingerprint=fingerprint,
                category=classification.category,
                action="recovery_ready",
                allowed=True,
                attempts=self.guard.attempts(
                    fingerprint
                ),
                reason="recovery was permitted but no executor was supplied",
            )

            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=guard_result,
                throttle=throttle_result,
                recovered=False,
                action="recover",
                reason="recovery permitted",
            )

        try:
            recovered = bool(recover())
        except Exception as exc:
            self.audit.record(
                fingerprint=fingerprint,
                category=classification.category,
                action="recovery_failed",
                allowed=False,
                attempts=self.guard.attempts(
                    fingerprint
                ),
                reason=f"recovery executor failed: {exc}",
            )

            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=guard_result,
                throttle=throttle_result,
                recovered=False,
                action="stop",
                reason=f"recovery executor failed: {exc}",
            )

        if recovered:
            self.audit.record(
                fingerprint=fingerprint,
                category=classification.category,
                action="recovery_success",
                allowed=True,
                attempts=self.guard.attempts(
                    fingerprint
                ),
                reason="recovery completed successfully",
            )

            return RuntimeRecoveryExecution(
                classification=classification,
                decision=decision,
                guard=guard_result,
                throttle=throttle_result,
                recovered=True,
                action="continue",
                reason="recovery completed successfully",
            )

        self.audit.record(
            fingerprint=fingerprint,
            category=classification.category,
            action="recovery_failed",
            allowed=False,
            attempts=self.guard.attempts(
                fingerprint
            ),
            reason="recovery executor reported failure",
        )

        return RuntimeRecoveryExecution(
            classification=classification,
            decision=decision,
            guard=guard_result,
            throttle=throttle_result,
            recovered=False,
            action="stop",
            reason="recovery executor reported failure",
        )
