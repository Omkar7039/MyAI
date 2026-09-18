from core.runtime_failure import (
    RuntimeFailureClassification,
    RuntimeFailureClassifier,
)


def test_no_failure():
    result = RuntimeFailureClassifier().classify()

    assert isinstance(result, RuntimeFailureClassification)
    assert result.category == "none"
    assert result.severity == "none"
    assert result.retryable is False
    assert result.recoverable is False
    assert result.confidence == 100


def test_timeout_failure():
    result = RuntimeFailureClassifier().classify(
        timed_out=True,
    )

    assert result.category == "timeout"
    assert result.severity == "high"
    assert result.retryable is True
    assert result.recoverable is True
    assert result.confidence == 100


def test_python_exception_categories():
    classifier = RuntimeFailureClassifier()

    assert classifier.classify(
        SyntaxError("bad syntax")
    ).category == "syntax"

    assert classifier.classify(
        NameError("missing")
    ).category == "name"

    assert classifier.classify(
        TypeError("wrong type")
    ).category == "type"

    assert classifier.classify(
        AssertionError("failed test")
    ).category == "assertion/test"


def test_environment_failure_is_retryable_and_recoverable():
    result = RuntimeFailureClassifier().classify(
        FileNotFoundError("missing file"),
    )

    assert result.category == "environment/tool"
    assert result.retryable is True
    assert result.recoverable is True


def test_state_failure_is_recoverable_but_not_retryable():
    result = RuntimeFailureClassifier().classify(
        message="malformed state detected",
    )

    assert result.category == "state"
    assert result.severity == "high"
    assert result.retryable is False
    assert result.recoverable is True


def test_runtime_failure_is_critical():
    result = RuntimeFailureClassifier().classify(
        message="runtime startup failed",
    )

    assert result.category == "runtime"
    assert result.severity == "critical"
    assert result.retryable is False
    assert result.recoverable is True


def test_semantic_failure_is_retryable():
    result = RuntimeFailureClassifier().classify(
        message="wrong result returned",
    )

    assert result.category == "semantic"
    assert result.retryable is True
    assert result.recoverable is False


def test_unknown_failure_preserves_error_detail():
    error = RuntimeError("unexpected database condition")

    result = RuntimeFailureClassifier().classify(
        error,
    )

    assert result.category == "unknown"
    assert result.severity == "high"
    assert result.retryable is False
    assert result.recoverable is False
    assert "unexpected database condition" in result.reasons[0]


def test_classification_is_deterministic():
    classifier = RuntimeFailureClassifier()

    first = classifier.classify(
        ConnectionError("connection refused"),
    )
    second = classifier.classify(
        ConnectionError("connection refused"),
    )

    assert first == second
