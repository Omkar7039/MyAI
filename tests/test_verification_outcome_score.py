from experience.learning_signal import LearningSignalCollector
from experience.verification_outcome_score import (
    VerificationOutcomeScorer,
)


def test_successful_property_verification_scores_90():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify add",
                strategy="property",
                attempts=1,
            ),
        ]
    )

    assert result.score == 90.0
    assert result.successful is True
    assert result.strategy_bonus == 20.0
    assert result.attempts_penalty == 0.0


def test_successful_mutation_verification_scores_90():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify parser",
                strategy="mutation",
            ),
        ]
    )

    assert result.score == 90.0
    assert result.strategy_bonus == 20.0


def test_successful_standard_verification_scores_80():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify fix",
                strategy="standard",
            ),
        ]
    )

    assert result.score == 80.0
    assert result.strategy_bonus == 10.0


def test_successful_unknown_strategy_scores_70():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify fix",
                strategy="custom",
            ),
        ]
    )

    assert result.score == 70.0
    assert result.strategy_bonus == 0.0


def test_failed_verification_gets_failure_penalty():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_failure(
                "verify fix",
                strategy="standard",
            ),
        ]
    )

    assert result.score == 0.0
    assert result.successful is False
    assert result.failure_penalty == 20.0


def test_extra_attempts_reduce_score():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify fix",
                strategy="property",
                attempts=3,
            ),
        ]
    )

    assert result.score == 70.0
    assert result.attempts_penalty == 20.0


def test_retry_reduces_score():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify fix",
                strategy="mutation",
            ),
            collector.retry(
                "verify fix",
                strategy="mutation",
            ),
        ]
    )

    assert result.score == 80.0
    assert result.retry_penalty == 10.0


def test_attempt_and_retry_penalties_combine():
    collector = LearningSignalCollector()

    result = VerificationOutcomeScorer().score(
        [
            collector.verification_success(
                "verify fix",
                strategy="property",
                attempts=3,
            ),
            collector.retry(
                "verify fix",
            ),
        ]
    )

    assert result.score == 60.0
    assert result.attempts_penalty == 20.0
    assert result.retry_penalty == 10.0


def test_empty_signals_are_safe():
    result = VerificationOutcomeScorer().score([])

    assert result.score == 0.0
    assert result.successful is False
    assert result.reasons == (
        "no verification outcome was recorded",
    )


def test_scoring_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            "verify fix",
            strategy="property",
            attempts=2,
        ),
        collector.retry("verify fix"),
    ]

    scorer = VerificationOutcomeScorer()

    first = scorer.score(signals)
    second = scorer.score(signals)

    assert first == second
