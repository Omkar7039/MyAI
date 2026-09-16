from __future__ import annotations

import pytest

from experience.learning_signal import LearningSignalCollector
from experience.safe_learning_control import SafeLearningControl


def make_signals(metadata="task_family=parser"):
    collector = LearningSignalCollector()

    return [
        collector.repair_success(
            "fix parser",
            strategy="property",
            score=95.0,
            metadata=metadata,
        ),
        collector.verification_success(
            "fix parser",
            strategy="property",
            score=95.0,
            metadata=metadata,
        ),
    ]


def test_matching_task_family_allows_improved_strategy():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals(),
        task_family="parser",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert result.strategy == "property"
    assert len(result.signals) == 2


def test_non_matching_task_family_blocks_strategy():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals("task_family=database"),
        task_family="parser",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is False
    assert result.rollback is False
    assert result.signals == ()
    assert "learning safety blocked" in result.reason


def test_missing_task_family_blocks_cross_task_learning():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals(),
        task_family="",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is False
    assert result.signals == ()
    assert "task family is required" in result.reason


def test_cross_task_disabled_allows_current_signals():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals("unscoped"),
        task_family=None,
        allow_cross_task=False,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert len(result.signals) == 2


def test_empty_signals_are_blocked():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=[],
        task_family="parser",
        allow_cross_task=False,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is False
    assert result.signals == ()
    assert "no learning signals" in result.reason


def test_high_regression_rolls_back_after_safety_passes():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals(),
        task_family="parser",
        allow_cross_task=True,
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert result.allowed is False
    assert result.rollback is True
    assert result.severity == "high"
    assert len(result.signals) == 2


def test_safety_failure_precedes_regression_control():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals("task_family=database"),
        task_family="parser",
        allow_cross_task=True,
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert result.allowed is False
    assert result.rollback is False
    assert result.severity == "none"
    assert "learning safety blocked" in result.reason


def test_nested_source_metadata_is_supported():
    result = SafeLearningControl().evaluate(
        strategy="property",
        signals=make_signals(
            "strategy=property; source_metadata=task_family=parser"
        ),
        task_family="parser",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is True
    assert len(result.signals) == 2


def test_strategy_is_rejected_when_empty():
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        SafeLearningControl().evaluate(
            strategy=" ",
            signals=make_signals(),
            task_family="parser",
            allow_cross_task=True,
            baseline_score=70.0,
            learned_score=95.0,
        )


def test_decision_is_deterministic():
    kwargs = {
        "strategy": "property",
        "signals": make_signals(),
        "task_family": "parser",
        "allow_cross_task": True,
        "baseline_score": 70.0,
        "learned_score": 95.0,
    }

    control = SafeLearningControl()

    first = control.evaluate(**kwargs)
    second = control.evaluate(**kwargs)

    assert first == second
