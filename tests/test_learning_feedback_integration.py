from experience.learning_feedback_integration import (
    AutomaticLearningFeedback,
)
from experience.learning_signal import LearningSignalType


def test_successful_outcome_is_ready_for_learning():
    result = AutomaticLearningFeedback().process(
        task="fix add",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=90.0,
        verification_score=95.0,
    )

    assert result.ready_for_learning is True
    assert len(result.signals) == 2
    assert result.feedback.score == 92.5


def test_failed_outcome_is_still_learning_ready():
    result = AutomaticLearningFeedback().process(
        task="fix parser",
        strategy="standard",
        repair_success=False,
        verification_success=False,
    )

    assert result.ready_for_learning is True
    assert result.feedback.score == 0.0
    assert result.signals[0].signal_type == (
        LearningSignalType.REPAIR_FAILURE
    )


def test_retry_and_rollback_are_preserved():
    result = AutomaticLearningFeedback().process(
        task="recover",
        strategy="multifile",
        repair_success=False,
        verification_success=False,
        attempts=3,
        retried=True,
        rolled_back=True,
    )

    assert [
        signal.signal_type
        for signal in result.signals
    ] == [
        LearningSignalType.REPAIR_FAILURE,
        LearningSignalType.VERIFICATION_FAILURE,
        LearningSignalType.RETRY,
        LearningSignalType.ROLLBACK,
    ]


def test_metadata_is_preserved():
    result = AutomaticLearningFeedback().process(
        task="fix",
        strategy="property",
        repair_success=True,
        verification_success=True,
        metadata="e2e",
    )

    assert all(
        signal.metadata == "e2e"
        for signal in result.signals
    )


def test_scores_are_normalized():
    result = AutomaticLearningFeedback().process(
        task="fix",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        repair_score=150.0,
        verification_score=-20.0,
    )

    assert result.feedback.signals[0].score == 100.0
    assert result.feedback.signals[1].score == 0.0
    assert result.feedback.score == 50.0


def test_strategy_is_preserved():
    result = AutomaticLearningFeedback().process(
        task="fix",
        strategy="  mutation  ",
        repair_success=True,
        verification_success=True,
    )

    assert result.feedback.strategy == "mutation"


def test_attempts_are_preserved():
    result = AutomaticLearningFeedback().process(
        task="fix",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        attempts=3,
    )

    assert all(
        signal.attempts == 3
        for signal in result.signals
    )


def test_custom_builder_is_respected():
    from experience.learning_feedback import (
        LearningFeedbackBuilder,
    )

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

    result = AutomaticLearningFeedback(
        builder=FixedBuilder(),
    ).process(
        task="ignored",
        strategy="standard",
        repair_success=False,
        verification_success=False,
    )

    assert result.feedback.strategy == "property"
    assert result.feedback.score == 100.0


def test_result_is_deterministic():
    processor = AutomaticLearningFeedback()

    kwargs = {
        "task": "fix",
        "strategy": "property",
        "repair_success": True,
        "verification_success": True,
        "attempts": 2,
        "repair_score": 90.0,
        "verification_score": 95.0,
    }

    first = processor.process(**kwargs)
    second = processor.process(**kwargs)

    assert first == second


def test_failed_verification_is_recorded():
    result = AutomaticLearningFeedback().process(
        task="verify",
        strategy="mutation",
        repair_success=True,
        verification_success=False,
        repair_score=90.0,
        verification_score=20.0,
    )

    assert result.signals[0].signal_type == (
        LearningSignalType.REPAIR_SUCCESS
    )
    assert result.signals[1].signal_type == (
        LearningSignalType.VERIFICATION_FAILURE
    )


def test_learning_control_allows_improved_outcome_without_extra_rollback():
    from experience.learning_control import LearningControlAdapter

    result = AutomaticLearningFeedback(
        control=LearningControlAdapter(),
    ).process(
        task="controlled success",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=90.0,
        verification_score=95.0,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert len(result.signals) == 2
    assert all(
        signal.signal_type
        not in {LearningSignalType.ROLLBACK}
        for signal in result.signals
    )


def test_learning_control_adds_rollback_for_high_regression():
    from experience.learning_control import LearningControlAdapter

    result = AutomaticLearningFeedback(
        control=LearningControlAdapter(),
    ).process(
        task="controlled regression",
        strategy="property",
        repair_success=False,
        verification_success=False,
        repair_score=40.0,
        verification_score=40.0,
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert len(result.signals) == 3
    assert result.signals[-1].signal_type == (
        LearningSignalType.ROLLBACK
    )


def test_existing_explicit_rollback_is_not_duplicated():
    from experience.learning_control import LearningControlAdapter

    result = AutomaticLearningFeedback(
        control=LearningControlAdapter(),
    ).process(
        task="already rolled back",
        strategy="property",
        repair_success=False,
        verification_success=False,
        repair_score=40.0,
        verification_score=40.0,
        rolled_back=True,
        baseline_score=95.0,
        learned_score=40.0,
    )

    rollback_count = sum(
        signal.signal_type == LearningSignalType.ROLLBACK
        for signal in result.signals
    )

    assert rollback_count == 1


def test_learning_control_is_optional():
    result = AutomaticLearningFeedback().process(
        task="ordinary",
        strategy="standard",
        repair_success=True,
        verification_success=True,
        repair_score=80.0,
        verification_score=80.0,
        baseline_score=90.0,
        learned_score=40.0,
    )

    assert len(result.signals) == 2


def test_control_scores_are_forwarded():
    from experience.learning_control import LearningControlAdapter

    result = AutomaticLearningFeedback(
        control=LearningControlAdapter(),
    ).process(
        task="forwarded scores",
        strategy="property",
        repair_success=True,
        verification_success=True,
        repair_score=90.0,
        verification_score=90.0,
        baseline_score=70.0,
        learned_score=90.0,
    )

    assert result.ready_for_learning is True
    assert result.feedback.strategy == "property"


def test_feedback_remains_deterministic_with_control():
    from experience.learning_control import LearningControlAdapter

    processor = AutomaticLearningFeedback(
        control=LearningControlAdapter(),
    )

    kwargs = {
        "task": "deterministic",
        "strategy": "property",
        "repair_success": False,
        "verification_success": False,
        "repair_score": 40.0,
        "verification_score": 40.0,
        "baseline_score": 90.0,
        "learned_score": 40.0,
    }

    first = processor.process(**kwargs)
    second = processor.process(**kwargs)

    assert first == second
