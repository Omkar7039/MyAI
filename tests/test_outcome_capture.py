import pytest

from experience.learning_feedback import LearningFeedbackBuilder
from experience.learning_signal import LearningSignalType
from experience.outcome_capture import AutomaticOutcomeCapture


def test_captures_successful_outcome():
    result = AutomaticOutcomeCapture().capture(
        task="fix add",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=90.0,
        verification_score=95.0,
    )

    assert result.captured is True
    assert result.task == "fix add"
    assert result.strategy == "property"
    assert result.feedback.score == 92.5
    assert len(result.feedback.signals) == 2


def test_captures_failed_outcome():
    result = AutomaticOutcomeCapture().capture(
        task="fix parser",
        strategy="standard",
        repair_success=False,
        verification_success=False,
    )

    assert result.captured is True
    assert result.feedback.score == 0.0
    assert result.feedback.signals[0].signal_type == (
        LearningSignalType.REPAIR_FAILURE
    )
    assert result.feedback.signals[1].signal_type == (
        LearningSignalType.VERIFICATION_FAILURE
    )


def test_retry_and_rollback_are_captured():
    result = AutomaticOutcomeCapture().capture(
        task="recover project",
        strategy="multifile",
        repair_success=False,
        verification_success=False,
        attempts=3,
        retried=True,
        rolled_back=True,
    )

    assert len(result.feedback.signals) == 4
    assert [
        signal.signal_type
        for signal in result.feedback.signals
    ] == [
        LearningSignalType.REPAIR_FAILURE,
        LearningSignalType.VERIFICATION_FAILURE,
        LearningSignalType.RETRY,
        LearningSignalType.ROLLBACK,
    ]


def test_scores_are_normalized():
    result = AutomaticOutcomeCapture().capture(
        task="clamped",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        repair_score=150.0,
        verification_score=-20.0,
    )

    assert result.feedback.signals[0].score == 100.0
    assert result.feedback.signals[1].score == 0.0
    assert result.feedback.score == 50.0


def test_task_and_strategy_are_trimmed():
    result = AutomaticOutcomeCapture().capture(
        task="  fix  ",
        strategy="  property  ",
        repair_success=True,
        verification_success=True,
    )

    assert result.task == "fix"
    assert result.strategy == "property"
    assert result.feedback.strategy == "property"


def test_empty_task_is_rejected():
    with pytest.raises(
        ValueError,
        match="task must not be empty",
    ):
        AutomaticOutcomeCapture().capture(
            task="   ",
            strategy="standard",
            repair_success=True,
            verification_success=True,
        )


def test_empty_strategy_is_rejected_by_feedback_layer():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        AutomaticOutcomeCapture().capture(
            task="fix",
            strategy="   ",
            repair_success=True,
            verification_success=True,
        )


def test_metadata_reaches_feedback_signals():
    result = AutomaticOutcomeCapture().capture(
        task="fix",
        strategy="mutation",
        repair_success=True,
        verification_success=True,
        metadata="automatic",
    )

    assert all(
        signal.metadata == "automatic"
        for signal in result.feedback.signals
    )


def test_custom_feedback_builder_is_used():
    class FixedBuilder(LearningFeedbackBuilder):
        def build(self, **kwargs):
            return super().build(
                task="custom",
                strategy="property",
                repair_success=True,
                verification_success=True,
                repair_score=100.0,
                verification_score=100.0,
            )

    result = AutomaticOutcomeCapture(
        feedback_builder=FixedBuilder(),
    ).capture(
        task="ignored",
        strategy="standard",
        repair_success=False,
        verification_success=False,
    )

    assert result.feedback.strategy == "property"
    assert result.feedback.score == 100.0


def test_capture_is_deterministic():
    capture = AutomaticOutcomeCapture()

    kwargs = {
        "task": "fix",
        "strategy": "property",
        "repair_success": True,
        "verification_success": True,
        "attempts": 2,
        "repair_score": 90.0,
        "verification_score": 95.0,
        "retried": True,
    }

    first = capture.capture(**kwargs)
    second = capture.capture(**kwargs)

    assert first == second


def test_capture_does_not_change_feedback_signals():
    result = AutomaticOutcomeCapture().capture(
        task="fix",
        strategy="standard",
        repair_success=True,
        verification_success=False,
        repair_score=80.0,
        verification_score=20.0,
    )

    assert result.feedback.repair_success is True
    assert result.feedback.verification_success is False
    assert result.feedback.signals[0].signal_type == (
        LearningSignalType.REPAIR_SUCCESS
    )
