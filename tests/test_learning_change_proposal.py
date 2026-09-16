from __future__ import annotations

import pytest

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_change_proposal import (
    LearningChangeProposalBuilder,
)
from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)
from experience.learning_regression import (
    LearningRegressionDetector,
)
from experience.learning_signal import LearningSignalCollector


def make_candidate():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    return AdaptiveStrategyRanker().best(
        signals,
        utility_by_strategy={"property": 90.0},
    )


def make_effectiveness(baseline=70.0, learned=90.0):
    return LearningEffectivenessEvaluator().evaluate(
        baseline_score=baseline,
        learned_score=learned,
    )


def make_regression(baseline=70.0, learned=90.0):
    return LearningRegressionDetector().detect(
        strategy="property",
        baseline_score=baseline,
        learned_score=learned,
    )


def test_builds_improvement_proposal():
    candidate = make_candidate()

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=make_effectiveness(),
        regression=make_regression(),
    )

    assert proposal.strategy == "property"
    assert proposal.current_score == 70.0
    assert proposal.proposed_score == 90.0
    assert proposal.observations == 5
    assert proposal.improvement == 20.0
    assert proposal.improved is True
    assert proposal.regression_detected is False
    assert proposal.regression_severity == "none"
    assert proposal.confidence == 40.0


def test_builds_neutral_proposal():
    candidate = make_candidate()

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=make_effectiveness(80.0, 80.0),
        regression=make_regression(80.0, 80.0),
    )

    assert proposal.improved is False
    assert proposal.regression_detected is False
    assert proposal.improvement == 0.0
    assert proposal.rationale == (
        "learned strategy matched the baseline"
    )


def test_builds_regression_proposal():
    candidate = make_candidate()

    effectiveness = make_effectiveness(90.0, 40.0)
    regression = make_regression(90.0, 40.0)

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    assert proposal.improved is False
    assert proposal.regression_detected is True
    assert proposal.regression_severity == "high"
    assert proposal.improvement == -50.0
    assert "regressed by 50.00 points" in proposal.rationale


def test_candidate_strategy_must_match_regression():
    candidate = make_candidate()

    collector = LearningSignalCollector()

    database_signals = [
        collector.repair_success(
            f"database-{index}",
            strategy="database",
            score=90.0,
        )
        for index in range(5)
    ]

    database_candidate = AdaptiveStrategyRanker().best(
        database_signals,
        utility_by_strategy={"database": 90.0},
    )

    with pytest.raises(
        ValueError,
        match="candidate and regression strategies must match",
    ):
        LearningChangeProposalBuilder().build(
            candidate=candidate,
            effectiveness=make_effectiveness(),
            regression=LearningRegressionDetector().detect(
                strategy=database_candidate.strategy,
                baseline_score=70.0,
                learned_score=90.0,
            ),
        )


def test_baseline_scores_must_match():
    candidate = make_candidate()

    with pytest.raises(
        ValueError,
        match="baseline scores must match",
    ):
        LearningChangeProposalBuilder().build(
            candidate=candidate,
            effectiveness=make_effectiveness(70.0, 90.0),
            regression=make_regression(80.0, 90.0),
        )


def test_learned_scores_must_match():
    candidate = make_candidate()

    with pytest.raises(
        ValueError,
        match="learned scores must match",
    ):
        LearningChangeProposalBuilder().build(
            candidate=candidate,
            effectiveness=make_effectiveness(70.0, 90.0),
            regression=make_regression(70.0, 80.0),
        )


def test_empty_candidate_strategy_is_rejected():
    candidate = make_candidate()
    candidate = candidate.__class__(
        strategy=" ",
        score=candidate.score,
        success_rate=candidate.success_rate,
        average_outcome_score=candidate.average_outcome_score,
        utility_score=candidate.utility_score,
        failure_penalty=candidate.failure_penalty,
        total_outcomes=candidate.total_outcomes,
    )

    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        LearningChangeProposalBuilder().build(
            candidate=candidate,
            effectiveness=make_effectiveness(),
            regression=make_regression(),
        )


def test_proposal_is_immutable():
    candidate = make_candidate()

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=make_effectiveness(),
        regression=make_regression(),
    )

    with pytest.raises(AttributeError):
        proposal.strategy = "mutation"


def test_proposal_is_deterministic():
    candidate = make_candidate()
    builder = LearningChangeProposalBuilder()

    first = builder.build(
        candidate=candidate,
        effectiveness=make_effectiveness(),
        regression=make_regression(),
    )

    second = builder.build(
        candidate=candidate,
        effectiveness=make_effectiveness(),
        regression=make_regression(),
    )

    assert first == second


def test_proposal_preserves_regression_confidence():
    candidate = make_candidate()

    effectiveness = make_effectiveness(90.0, 60.0)
    regression = make_regression(90.0, 60.0)

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    assert proposal.confidence == 60.0
    assert proposal.regression_severity == "high"
