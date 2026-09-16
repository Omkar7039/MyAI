import pytest

from experience.adaptive_strategy import AdaptiveStrategyScore
from experience.learning_policy import LearningPolicy


def candidate(
    *,
    strategy="property",
    score=90.0,
    success_rate=100.0,
    total_outcomes=5,
):
    return AdaptiveStrategyScore(
        strategy=strategy,
        score=score,
        success_rate=success_rate,
        average_outcome_score=90.0,
        utility_score=80.0,
        failure_penalty=0.0,
        total_outcomes=total_outcomes,
    )


def test_sufficient_evidence_allows_learning():
    result = LearningPolicy().decide(candidate())

    assert result.allowed is True
    assert result.strategy == "property"
    assert result.confidence == pytest.approx(45.0)
    assert result.reason == "historical evidence is sufficient"


def test_insufficient_observations_block_learning():
    result = LearningPolicy().decide(
        candidate(total_outcomes=2),
    )

    assert result.allowed is False
    assert result.strategy == "property"
    assert result.reason == (
        "insufficient historical observations"
    )


def test_low_success_rate_blocks_learning():
    result = LearningPolicy().decide(
        candidate(success_rate=60.0),
    )

    assert result.allowed is False
    assert result.reason == (
        "historical success rate is below policy threshold"
    )


def test_low_score_blocks_learning():
    result = LearningPolicy().decide(
        candidate(score=60.0),
    )

    assert result.allowed is False
    assert result.reason == (
        "adaptive strategy score is below policy threshold"
    )


def test_no_candidate_is_safe():
    result = LearningPolicy().decide(None)

    assert result.allowed is False
    assert result.strategy is None
    assert result.confidence == 0.0
    assert result.reason == "no historical strategy evidence"


def test_custom_thresholds_are_respected():
    policy = LearningPolicy(
        min_observations=2,
        min_success_rate=80.0,
        min_score=80.0,
    )

    result = policy.decide(
        candidate(
            score=80.0,
            success_rate=80.0,
            total_outcomes=2,
        )
    )

    assert result.allowed is True


def test_confidence_increases_with_more_observations():
    policy = LearningPolicy()

    low = policy.decide(
        candidate(total_outcomes=3),
    )
    high = policy.decide(
        candidate(total_outcomes=10),
    )

    assert high.confidence > low.confidence


def test_confidence_is_bounded():
    policy = LearningPolicy()

    result = policy.decide(
        candidate(
            score=100.0,
            success_rate=100.0,
            total_outcomes=100,
        )
    )

    assert 0.0 <= result.confidence <= 100.0
    assert result.confidence == 100.0


def test_invalid_minimum_observations_are_rejected():
    with pytest.raises(
        ValueError,
        match="min_observations must be at least 1",
    ):
        LearningPolicy(min_observations=0)


def test_invalid_success_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_success_rate must be between 0 and 100",
    ):
        LearningPolicy(min_success_rate=101.0)


def test_invalid_score_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="min_score must be between 0 and 100",
    ):
        LearningPolicy(min_score=-1.0)


def test_policy_is_deterministic():
    policy = LearningPolicy()
    item = candidate()

    first = policy.decide(item)
    second = policy.decide(item)

    assert first == second
