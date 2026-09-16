from __future__ import annotations

import pytest

from experience.governed_strategy_router import (
    GovernedStrategyRouter,
)
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


def test_strong_governed_candidate_is_selected():
    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=make_signals(),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.governed is True
    assert result.confidence >= 50.0


def test_neutral_candidate_falls_back_to_default():
    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=make_signals(score=80.0),
        baseline_score=80.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 80.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.governed is True


def test_regressed_candidate_falls_back_to_default():
    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=make_signals(score=40.0),
        baseline_score=100.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 40.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.governed is True


def test_cross_task_safety_falls_back_to_default():
    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=make_signals(
            metadata="task_family=database"
        ),
        baseline_score=70.0,
        task_family="parser",
        allow_cross_task=True,
        utility_by_strategy={"property": 100.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.governed is False
    assert "governance rejected" in result.reason


def test_empty_history_uses_default():
    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=[],
        baseline_score=70.0,
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.governed is False


def test_default_strategy_is_trimmed():
    result = GovernedStrategyRouter().route(
        default_strategy="  standard  ",
        signals=[],
        baseline_score=70.0,
    )

    assert result.strategy == "standard"


def test_empty_default_strategy_is_rejected():
    with pytest.raises(
        ValueError,
        match="default_strategy must not be empty",
    ):
        GovernedStrategyRouter().route(
            default_strategy=" ",
            signals=[],
            baseline_score=70.0,
        )


def test_custom_governed_adapter_is_respected():
    from experience.governed_learning import (
        GovernedLearningAdapter,
    )

    class EmptyGoverned(GovernedLearningAdapter):
        def evaluate(self, **kwargs):
            from experience.governed_learning import (
                GovernedLearningResult,
            )

            return GovernedLearningResult(
                candidate_strategy=None,
                proposal=None,
                governance=None,
                safe=True,
                reason="custom adapter",
            )

    result = GovernedStrategyRouter(
        governed=EmptyGoverned(),
    ).route(
        default_strategy="standard",
        signals=[],
        baseline_score=70.0,
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.reason.startswith(
        "governance rejected learned strategy"
    )


def test_control_requires_real_governance_application():
    from experience.governed_learning import (
        GovernedLearningResult,
    )

    class NotAppliedGoverned:
        def evaluate(self, **kwargs):
            from experience.learning_governance import (
                LearningGovernanceDecision,
            )

            return GovernedLearningResult(
                candidate_strategy="property",
                proposal=None,
                governance=LearningGovernanceDecision(
                    approved=True,
                    applied=False,
                    strategy="property",
                    confidence=80.0,
                    reason="not applied",
                    change=None,
                ),
                safe=True,
                reason="not applied",
            )

    result = GovernedStrategyRouter(
        governed=NotAppliedGoverned(),
    ).route(
        default_strategy="standard",
        signals=[],
        baseline_score=70.0,
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_result_is_deterministic():
    signals = make_signals()

    kwargs = {
        "default_strategy": "standard",
        "signals": signals,
        "baseline_score": 70.0,
        "task_family": "parser",
        "allow_cross_task": True,
        "utility_by_strategy": {"property": 100.0},
    }

    first = GovernedStrategyRouter().route(**kwargs)
    second = GovernedStrategyRouter().route(**kwargs)

    assert first == second
