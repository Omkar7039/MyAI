from __future__ import annotations

import pytest

from experience.governed_learning import GovernedLearningAdapter
from experience.learning_signal import LearningSignalCollector


def make_signals(
    *,
    strategy="property",
    score=100.0,
    metadata="task_family=parser",
    count=5,
):
    collector = LearningSignalCollector()

    return [
        collector.repair_success(
            f"task-{index}",
            strategy=strategy,
            score=score,
            metadata=metadata,
        )
        for index in range(count)
    ]


def test_strong_candidate_can_be_governed_and_applied():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(score=100.0),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.safe is True
    assert result.candidate_strategy == "property"
    assert result.proposal is not None
    assert result.governance is not None
    assert result.governance.approved is True
    assert result.governance.applied is True


def test_candidate_score_is_used_as_learned_score():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(score=100.0),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.proposal is not None
    assert result.proposal.proposed_score == 100.0
    assert result.proposal.current_score == 70.0


def test_neutral_candidate_is_not_applied():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(score=80.0),
        baseline_score=80.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 80.0},
    )

    assert result.safe is True
    assert result.candidate_strategy == "property"
    assert result.governance is not None
    assert result.governance.approved is False
    assert result.governance.applied is False


def test_cross_task_safety_blocks_candidate():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(
            metadata="task_family=database",
            score=100.0,
        ),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.safe is False
    assert result.candidate_strategy is None
    assert result.proposal is None
    assert result.governance is None
    assert "no learning signals match" in result.reason


def test_no_signals_are_safe_but_unusable():
    result = GovernedLearningAdapter().evaluate(
        signals=[],
        baseline_score=70.0,
    )

    assert result.safe is False
    assert result.candidate_strategy is None
    assert result.proposal is None
    assert result.governance is None
    assert "no learning signals available" in result.reason


def test_insufficient_history_has_no_candidate():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(count=2),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.safe is True
    assert result.candidate_strategy == "property"
    assert result.proposal is not None
    assert result.governance is not None
    assert result.governance.approved is False
    assert "insufficient" in result.governance.reason


def test_large_regression_is_rejected():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(score=40.0),
        baseline_score=100.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 40.0},
    )

    assert result.proposal is not None
    assert result.proposal.regression_detected is True
    assert result.governance is not None
    assert result.governance.approved is False
    assert result.governance.applied is False


def test_cross_task_disabled_allows_unscoped_signals():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(
            metadata="unscoped",
            score=100.0,
        ),
        baseline_score=70.0,
        allow_cross_task=False,
        utility_by_strategy={"property": 100.0},
    )

    assert result.safe is True
    assert result.candidate_strategy == "property"


def test_custom_utility_can_affect_candidate_selection():
    result = GovernedLearningAdapter().evaluate(
        signals=(
            *make_signals(
                strategy="property",
                score=90.0,
                metadata="task_family=parser",
                count=5,
            ),
            *make_signals(
                strategy="mutation",
                score=95.0,
                metadata="task_family=parser",
                count=5,
            ),
        ),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={
            "property": 100.0,
            "mutation": 0.0,
        },
    )

    assert result.candidate_strategy == "property"


def test_result_is_deterministic():
    signals = make_signals(score=100.0)

    kwargs = {
        "signals": signals,
        "baseline_score": 70.0,
        "task_family": "parser",
        "allow_cross_task": True,
        "utility_by_strategy": {"property": 100.0},
    }

    first = GovernedLearningAdapter().evaluate(**kwargs)
    second = GovernedLearningAdapter().evaluate(**kwargs)

    assert first == second


def test_empty_task_family_blocks_cross_task_learning():
    result = GovernedLearningAdapter().evaluate(
        signals=make_signals(),
        baseline_score=70.0,
        task_family=" ",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.safe is False
    assert result.proposal is None
    assert "task family is required" in result.reason


def test_baseline_score_validation_is_preserved():
    with pytest.raises(
        ValueError,
        match="baseline_score",
    ):
        GovernedLearningAdapter().evaluate(
            signals=make_signals(),
            baseline_score=101.0,
        )


def test_custom_governance_controller_is_respected():
    from experience.learning_governance import (
        LearningGovernanceController,
    )

    controller = LearningGovernanceController()

    result = GovernedLearningAdapter(
        governance=controller,
    ).evaluate(
        signals=make_signals(score=100.0),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.governance is not None
    assert result.governance is not None
    assert result.governance.change is not None
    assert controller.get_applied("property") is not None
