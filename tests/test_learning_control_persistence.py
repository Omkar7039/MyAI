from __future__ import annotations

import pytest

from experience.learning_control import LearningControlAdapter
from experience.learning_control_persistence import (
    ControlledLearningPersistence,
)
from experience.learning_persistence import LearningPersistenceBridge
from experience.learning_signal import LearningSignalCollector
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "experiences.db")
    )


def make_signals():
    collector = LearningSignalCollector()

    return [
        collector.repair_success(
            "fix add",
            strategy="property",
            score=95.0,
        ),
        collector.verification_success(
            "fix add",
            strategy="property",
            score=95.0,
        ),
    ]


def test_improved_learning_is_persisted(tmp_path):
    store = make_store(tmp_path)

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
        LearningControlAdapter(),
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert result.persistence is not None
    assert result.persistence.persisted == 2


def test_high_regression_is_not_persisted(tmp_path):
    store = make_store(tmp_path)

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
        LearningControlAdapter(),
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert result.allowed is False
    assert result.rollback is True
    assert result.persistence is None

    assert store.recent(limit=20) == []


def test_neutral_learning_can_be_persisted(tmp_path):
    store = make_store(tmp_path)

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=90.0,
        learned_score=90.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert result.persistence is not None
    assert result.persistence.persisted == 2


def test_low_regression_remains_persistable(tmp_path):
    store = make_store(tmp_path)

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=90.0,
        learned_score=82.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert result.persistence is not None


def test_custom_control_threshold_is_respected(tmp_path):
    from experience.continuous_learning import (
        ContinuousLearningController,
    )

    store = make_store(tmp_path)

    control = LearningControlAdapter(
        ContinuousLearningController(
            rollback_severity="medium",
        )
    )

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
        control,
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=90.0,
        learned_score=70.0,
    )

    assert result.allowed is False
    assert result.rollback is True
    assert result.persistence is None
    assert store.recent(limit=20) == []


def test_duplicate_persistence_remains_safe(tmp_path):
    store = make_store(tmp_path)
    bridge = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
    )

    first = bridge.persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=70.0,
        learned_score=95.0,
    )
    second = bridge.persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert first.persistence is not None
    assert second.persistence is not None
    assert first.persistence.persisted == 2
    assert second.persistence.persisted == 0
    assert second.persistence.skipped == 2


def test_empty_signal_list_is_safe(tmp_path):
    result = ControlledLearningPersistence(
        LearningPersistenceBridge(make_store(tmp_path)),
    ).persist(
        signals=[],
        strategy="property",
        baseline_score=70.0,
        learned_score=90.0,
    )

    assert result.allowed is True
    assert result.rollback is False
    assert result.persistence is not None
    assert result.persistence.persisted == 0


def test_empty_strategy_is_rejected(tmp_path):
    with pytest.raises(
        ValueError,
        match="strategy must not be empty",
    ):
        ControlledLearningPersistence(
            LearningPersistenceBridge(make_store(tmp_path)),
        ).persist(
            signals=[],
            strategy="   ",
            baseline_score=70.0,
            learned_score=90.0,
        )


def test_scores_are_validated(tmp_path):
    bridge = ControlledLearningPersistence(
        LearningPersistenceBridge(make_store(tmp_path)),
    )

    with pytest.raises(ValueError):
        bridge.persist(
            signals=[],
            strategy="property",
            baseline_score=-1.0,
            learned_score=90.0,
        )

    with pytest.raises(ValueError):
        bridge.persist(
            signals=[],
            strategy="property",
            baseline_score=70.0,
            learned_score=101.0,
        )


def test_persistence_is_not_called_when_blocked(tmp_path):
    class TrackingPersistence(LearningPersistenceBridge):
        def __init__(self, store):
            super().__init__(store)
            self.calls = 0

        def persist(self, signals):
            self.calls += 1
            return super().persist(signals)

    persistence = TrackingPersistence(make_store(tmp_path))

    result = ControlledLearningPersistence(
        persistence,
    ).persist(
        signals=make_signals(),
        strategy="property",
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert result.allowed is False
    assert persistence.calls == 0
