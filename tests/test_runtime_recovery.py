from core.runtime_failure import RuntimeFailureClassifier
from core.runtime_recovery import (
    RuntimeRecoveryDecision,
    RuntimeRecoveryDecisionEngine,
)


def classify(*args, **kwargs):
    return RuntimeFailureClassifier().classify(
        *args,
        **kwargs,
    )


def test_no_failure_continues():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(),
    )

    assert isinstance(result, RuntimeRecoveryDecision)
    assert result.action == "continue"
    assert result.safe_to_continue is True


def test_state_failure_requires_recovery():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            message="malformed state detected",
        ),
    )

    assert result.action == "recover"
    assert result.safe_to_continue is False
    assert "recoverable" in result.reason


def test_runtime_failure_requires_recovery():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            message="runtime startup failed",
        ),
    )

    assert result.action == "recover"
    assert result.safe_to_continue is False


def test_timeout_requests_retry():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            timed_out=True,
        ),
    )

    assert result.action == "retry"
    assert result.safe_to_continue is False


def test_environment_failure_requests_recovery():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            FileNotFoundError("missing file"),
        ),
    )

    assert result.action == "recover"
    assert result.safe_to_continue is False


def test_assertion_failure_requests_retry():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            AssertionError("test failed"),
        ),
    )

    assert result.action == "retry"
    assert result.safe_to_continue is False


def test_semantic_failure_requests_retry():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            message="wrong result returned",
        ),
    )

    assert result.action == "retry"
    assert result.safe_to_continue is False


def test_syntax_failure_stops():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            SyntaxError("invalid syntax"),
        ),
    )

    assert result.action == "stop"
    assert result.safe_to_continue is False


def test_name_failure_stops():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            NameError("missing_name"),
        ),
    )

    assert result.action == "stop"
    assert result.safe_to_continue is False


def test_type_failure_stops():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            TypeError("wrong type"),
        ),
    )

    assert result.action == "stop"
    assert result.safe_to_continue is False


def test_unknown_failure_stops():
    result = RuntimeRecoveryDecisionEngine().decide(
        classify(
            RuntimeError("unexpected failure"),
        ),
    )

    assert result.action == "stop"
    assert result.safe_to_continue is False


def test_decision_is_deterministic():
    engine = RuntimeRecoveryDecisionEngine()
    classification = classify(
        timed_out=True,
    )

    first = engine.decide(classification)
    second = engine.decide(classification)

    assert first == second
