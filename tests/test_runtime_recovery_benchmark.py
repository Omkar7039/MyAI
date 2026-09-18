from __future__ import annotations

import time

from core.runtime_failure import RuntimeFailureClassifier
from core.runtime_recovery import RuntimeRecoveryDecisionEngine
from core.runtime_recovery_audit import RuntimeRecoveryAudit
from core.runtime_recovery_guard import RuntimeRecoveryGuard
from core.runtime_recovery_throttle import RuntimeRecoveryThrottle


def _measure(operation, iterations: int) -> float:
    start = time.perf_counter()

    for _ in range(iterations):
        operation()

    return time.perf_counter() - start


def test_failure_classification_benchmark():
    classifier = RuntimeFailureClassifier()
    iterations = 5000

    elapsed = _measure(
        lambda: classifier.classify(
            timed_out=True,
        ),
        iterations,
    )

    result = classifier.classify(
        timed_out=True,
    )

    assert result.category == "timeout"
    assert elapsed < 2.0

    print(
        f"\nRuntimeFailureClassifier: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_recovery_decision_benchmark():
    classifier = RuntimeFailureClassifier()
    engine = RuntimeRecoveryDecisionEngine()

    classification = classifier.classify(
        message="malformed state detected",
    )

    iterations = 5000

    elapsed = _measure(
        lambda: engine.decide(classification),
        iterations,
    )

    result = engine.decide(classification)

    assert result.action == "recover"
    assert elapsed < 2.0

    print(
        f"\nRuntimeRecoveryDecisionEngine: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_recovery_guard_benchmark():
    guard = RuntimeRecoveryGuard(
        max_attempts=100000,
    )

    iterations = 5000

    elapsed = _measure(
        lambda: guard.check("state:learning"),
        iterations,
    )

    result = guard.check("state:learning")

    assert result.allowed is True
    assert elapsed < 2.0

    print(
        f"\nRuntimeRecoveryGuard: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_recovery_throttle_benchmark():
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5.0,
    )

    iterations = 5000

    elapsed = _measure(
        lambda: throttle.check("state:learning"),
        iterations,
    )

    result = throttle.check("state:learning")

    assert result.allowed is True
    assert elapsed < 2.0

    print(
        f"\nRuntimeRecoveryThrottle: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_recovery_audit_benchmark(tmp_path):
    audit = RuntimeRecoveryAudit(
        tmp_path / "recovery_audit.db",
    )

    iterations = 250

    elapsed = _measure(
        lambda: audit.record(
            fingerprint="state:learning",
            category="state",
            action="recover",
            allowed=True,
            attempts=1,
            reason="benchmark recovery",
        ),
        iterations,
    )

    assert audit.count() == iterations
    assert elapsed < 2.0

    recent = audit.recent(limit=5)

    assert len(recent) == 5
    assert recent[0].fingerprint == "state:learning"

    print(
        f"\nRuntimeRecoveryAudit: "
        f"{elapsed:.4f}s/{iterations}"
    )


def test_full_recovery_pipeline_benchmark(tmp_path):
    classifier = RuntimeFailureClassifier()
    decision_engine = RuntimeRecoveryDecisionEngine()
    guard = RuntimeRecoveryGuard(
        max_attempts=100000,
    )
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=0,
    )
    audit = RuntimeRecoveryAudit(
        tmp_path / "pipeline_audit.db",
    )

    iterations = 250

    def pipeline():
        classification = classifier.classify(
            timed_out=True,
        )

        decision = decision_engine.decide(
            classification,
        )

        fingerprint = "timeout:benchmark"

        guard_result = guard.check(
            fingerprint,
        )

        if decision.action == "retry" and guard_result.allowed:
            throttle_result = throttle.check(
                fingerprint,
            )

            if throttle_result.allowed:
                guard.record(
                    fingerprint,
                )

                audit.record(
                    fingerprint=fingerprint,
                    category=classification.category,
                    action=decision.action,
                    allowed=False,
                    attempts=guard.attempts(
                        fingerprint,
                    ),
                    reason=decision.reason,
                )

    elapsed = _measure(
        pipeline,
        iterations,
    )

    assert audit.count() == iterations
    assert elapsed < 2.0

    print(
        f"\nFull recovery pipeline: "
        f"{elapsed:.4f}s/{iterations}"
    )
