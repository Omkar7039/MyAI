from experience.learning_signal import (
    LearningSignalCollector,
)
from experience.repair_outcome_score import (
    RepairOutcomeScorer,
)


def test_successful_repair_scores_70():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "fix add",
                attempts=1,
            ),
        ]
    )

    assert result.score == 70.0
    assert result.successful is True
    assert result.attempts_penalty == 0.0
    assert result.verification_bonus == 0.0
    assert result.rollback_penalty == 0.0


def test_successful_verified_repair_scores_90():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "fix add",
                attempts=1,
            ),
            collector.verification_success(
                "verify add",
            ),
        ]
    )

    assert result.score == 90.0
    assert result.successful is True
    assert result.verification_bonus == 20.0


def test_failed_repair_scores_zero():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_failure(
                "fix parser",
                attempts=1,
            ),
        ]
    )

    assert result.score == 0.0
    assert result.successful is False


def test_extra_attempts_reduce_score():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "fix parser",
                attempts=3,
            ),
        ]
    )

    assert result.score == 50.0
    assert result.attempts_penalty == 20.0


def test_verification_failure_does_not_add_bonus():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "fix parser",
            ),
            collector.verification_failure(
                "verify parser",
                score=20.0,
            ),
        ]
    )

    assert result.score == 70.0
    assert result.verification_bonus == 0.0
    assert result.successful is True


def test_rollback_applies_penalty():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "fix project",
            ),
            collector.rollback(
                "fix project",
            ),
        ]
    )

    assert result.score == 40.0
    assert result.rollback_penalty == 30.0


def test_rollback_and_retries_are_combined():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_failure(
                "repair",
                attempts=3,
            ),
            collector.retry(
                "repair",
                attempts=3,
            ),
            collector.rollback(
                "repair",
                attempts=3,
            ),
        ]
    )

    assert result.score == 0.0
    assert result.attempts_penalty == 20.0
    assert result.rollback_penalty == 30.0


def test_attempt_penalty_is_capped():
    collector = LearningSignalCollector()

    result = RepairOutcomeScorer().score(
        [
            collector.repair_success(
                "repair",
                attempts=10,
            ),
        ]
    )

    assert result.attempts_penalty == 20.0
    assert result.score == 50.0


def test_empty_signals_are_safe():
    result = RepairOutcomeScorer().score([])

    assert result.score == 0.0
    assert result.successful is False
    assert result.attempts_penalty == 0.0
    assert result.verification_bonus == 0.0
    assert result.rollback_penalty == 0.0


def test_scoring_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "fix",
            attempts=2,
        ),
        collector.verification_success(
            "verify",
        ),
    ]

    scorer = RepairOutcomeScorer()

    first = scorer.score(signals)
    second = scorer.score(signals)

    assert first == second
