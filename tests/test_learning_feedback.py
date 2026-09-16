import pytest

from experience.learning_feedback import LearningFeedbackBuilder
from experience.learning_signal import LearningSignalType


def test_successful_repair_and_verification_create_two_signals():
    result = LearningFeedbackBuilder().build(
        task="fix add",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=90.0,
        verification_score=95.0,
    )

    assert len(result.signals) == 2
    assert result.signals[0].signal_type == (
        LearningSignalType.REPAIR_SUCCESS
    )
    assert result.signals[1].signal_type == (
        LearningSignalType.VERIFICATION_SUCCESS
    )
    assert result.repair_success is True
    assert result.verification_success is True
    assert result.score == 92.5


def test_failed_repair_creates_failure_signal():
    result = LearningFeedbackBuilder().build(
        task="fix parser",
        strategy="standard",
        repair_success=False,
        verification_success=False,
        repair_score=0.0,
        verification_score=0.0,
    )

    assert len(result.signals) == 2
    assert result.signals[0].signal_type == (
        LearningSignalType.REPAIR_FAILURE
    )
    assert result.signals[1].signal_type == (
        LearningSignalType.VERIFICATION_FAILURE
    )
    assert result.score == 0.0


def test_retry_adds_retry_signal():
    result = LearningFeedbackBuilder().build(
        task="retry repair",
        strategy="mutation",
        repair_success=True,
        verification_success=True,
        attempts=2,
        repair_score=90.0,
        verification_score=90.0,
        retried=True,
    )

    assert len(result.signals) == 3
    assert result.signals[-1].signal_type == (
        LearningSignalType.RETRY
    )


def test_rollback_adds_rollback_signal():
    result = LearningFeedbackBuilder().build(
        task="rollback repair",
        strategy="multifile",
        repair_success=False,
        verification_success=False,
        attempts=3,
        rolled_back=True,
    )

    assert len(result.signals) == 3
    assert result.signals[-1].signal_type == (
        LearningSignalType.ROLLBACK
    )


def test_retry_and_rollback_can_be_recorded_together():
    result = LearningFeedbackBuilder().build(
        task="recover",
        strategy="multifile",
        repair_success=False,
        verification_success=False,
        attempts=3,
        retried=True,
        rolled_back=True,
    )

    assert len(result.signals) == 4
    assert [
        signal.signal_type
        for signal in result.signals
    ] == [
        LearningSignalType.REPAIR_FAILURE,
        LearningSignalType.VERIFICATION_FAILURE,
        LearningSignalType.RETRY,
        LearningSignalType.ROLLBACK,
    ]


def test_partial_success_reduces_combined_score():
    result = LearningFeedbackBuilder().build(
        task="partial",
        strategy="standard",
        repair_success=True,
        verification_success=False,
        repair_score=100.0,
        verification_score=80.0,
    )

    assert result.score == 45.0


def test_scores_are_clamped():
    result = LearningFeedbackBuilder().build(
        task="clamped",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        repair_score=150.0,
        verification_score=-20.0,
    )

    assert result.score == 50.0


def test_strategy_is_normalized():
    result = LearningFeedbackBuilder().build(
        task="fix",
        strategy="  PROPERTY  ",
        repair_success=True,
        verification_success=True,
    )

    assert result.strategy == "PROPERTY"


def test_empty_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        LearningFeedbackBuilder().build(
            task="fix",
            strategy="   ",
            repair_success=True,
            verification_success=True,
        )


def test_metadata_is_propagated():
    result = LearningFeedbackBuilder().build(
        task="fix",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        metadata="post-repair",
    )

    assert all(
        signal.metadata == "post-repair"
        for signal in result.signals
    )


def test_feedback_is_deterministic():
    builder = LearningFeedbackBuilder()

    first = builder.build(
        task="fix",
        strategy="property",
        repair_success=True,
        verification_success=True,
        attempts=2,
        repair_score=90.0,
        verification_score=95.0,
        retried=True,
    )

    second = builder.build(
        task="fix",
        strategy="property",
        repair_success=True,
        verification_success=True,
        attempts=2,
        repair_score=90.0,
        verification_score=95.0,
        retried=True,
    )

    assert first == second
