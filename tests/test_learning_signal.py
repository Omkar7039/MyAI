import pytest

from experience.learning_signal import (
    LearningSignalCollector,
    LearningSignalType,
)


def test_repair_success_signal():
    signal = LearningSignalCollector().repair_success(
        "fix add function",
        strategy="standard",
        attempts=2,
        score=95.0,
    )

    assert signal.signal_type == LearningSignalType.REPAIR_SUCCESS
    assert signal.task == "fix add function"
    assert signal.strategy == "standard"
    assert signal.attempts == 2
    assert signal.score == 95.0


def test_repair_failure_signal():
    signal = LearningSignalCollector().repair_failure(
        "fix parser",
        strategy="mutation",
        attempts=3,
    )

    assert signal.signal_type == LearningSignalType.REPAIR_FAILURE
    assert signal.strategy == "mutation"
    assert signal.attempts == 3
    assert signal.score == 0.0


def test_verification_success_signal():
    signal = LearningSignalCollector().verification_success(
        "verify repair",
        strategy="property",
        score=100.0,
    )

    assert signal.signal_type == LearningSignalType.VERIFICATION_SUCCESS
    assert signal.strategy == "property"
    assert signal.score == 100.0


def test_verification_failure_signal():
    signal = LearningSignalCollector().verification_failure(
        "verify repair",
        strategy="mutation",
        attempts=2,
        score=30.0,
    )

    assert signal.signal_type == LearningSignalType.VERIFICATION_FAILURE
    assert signal.attempts == 2
    assert signal.score == 30.0


def test_retry_signal():
    signal = LearningSignalCollector().retry(
        "repair project",
        strategy="repair",
        attempts=2,
    )

    assert signal.signal_type == LearningSignalType.RETRY
    assert signal.attempts == 2


def test_rollback_signal():
    signal = LearningSignalCollector().rollback(
        "repair project",
        strategy="multifile",
        attempts=3,
        metadata="rollback confirmed",
    )

    assert signal.signal_type == LearningSignalType.ROLLBACK
    assert signal.metadata == "rollback confirmed"


def test_task_is_normalized():
    signal = LearningSignalCollector().repair_success(
        "  fix bug  ",
        strategy="  standard  ",
        metadata="  note  ",
    )

    assert signal.task == "fix bug"
    assert signal.strategy == "standard"
    assert signal.metadata == "note"


def test_empty_task_is_rejected():
    with pytest.raises(ValueError, match="task must not be empty"):
        LearningSignalCollector().repair_success("   ")


def test_invalid_attempt_count_is_rejected():
    with pytest.raises(
        ValueError,
        match="attempts must be at least 1",
    ):
        LearningSignalCollector().repair_success(
            "fix bug",
            attempts=0,
        )


def test_invalid_score_is_rejected():
    collector = LearningSignalCollector()

    with pytest.raises(
        ValueError,
        match="score must be between 0 and 100",
    ):
        collector.repair_success("fix bug", score=101.0)

    with pytest.raises(
        ValueError,
        match="score must be between 0 and 100",
    ):
        collector.repair_success("fix bug", score=-1.0)


def test_signal_creation_is_deterministic():
    collector = LearningSignalCollector()

    first = collector.verification_success(
        "verify bug",
        strategy="property",
        attempts=2,
        score=88.0,
        metadata="stable",
    )
    second = collector.verification_success(
        "verify bug",
        strategy="property",
        attempts=2,
        score=88.0,
        metadata="stable",
    )

    assert first == second
