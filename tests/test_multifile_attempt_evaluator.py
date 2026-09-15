from agents.multifile_attempt_evaluator import (
    MultiFileAttemptEvaluator,
)


def test_successful_attempt_is_not_retryable():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": True,
            "stage": "complete",
            "errors": [],
            "rolled_back": False,
        }
    )

    assert result.retryable is False
    assert result.severity == "none"


def test_planning_failure_is_retryable():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": False,
            "stage": "planning",
            "errors": ["planner failed"],
            "rolled_back": False,
        }
    )

    assert result.retryable is True
    assert result.severity == "high"
    assert "new repair plan" in result.reason


def test_validation_failure_is_retryable():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": False,
            "stage": "validation",
            "errors": ["unsafe patch"],
            "rolled_back": False,
        }
    )

    assert result.retryable is True
    assert result.severity == "high"


def test_post_apply_failure_is_retryable():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": False,
            "stage": "post_apply_verification",
            "errors": ["test failed"],
            "rolled_back": True,
        }
    )

    assert result.retryable is True
    assert result.severity == "high"
    assert "rolled back" in result.reason


def test_unknown_failure_without_evidence_stops_safely():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": False,
            "stage": "unknown",
            "errors": [],
            "rolled_back": False,
        }
    )

    assert result.retryable is False
    assert result.severity == "unknown"


def test_generic_error_is_retryable():
    result = MultiFileAttemptEvaluator().evaluate(
        {
            "success": False,
            "stage": "execution",
            "errors": ["unexpected execution error"],
            "rolled_back": False,
        }
    )

    assert result.retryable is True
    assert result.severity == "medium"


def test_evaluation_is_deterministic():
    attempt = {
        "success": False,
        "stage": "validation",
        "errors": ["invalid patch"],
        "rolled_back": False,
    }

    evaluator = MultiFileAttemptEvaluator()

    first = evaluator.evaluate(attempt)
    second = evaluator.evaluate(attempt)

    assert first == second
