from __future__ import annotations

from experience.learning_control import LearningControlAdapter
from experience.learning_control_benchmark import LearningControlBenchmark
from experience.learning_control_persistence import (
    ControlledLearningPersistence,
)
from experience.learning_control_persistence import (
    ControlledPersistenceResult,
)
from experience.learning_orchestrator import UnifiedLearningRouter
from experience.learning_persistence import LearningPersistenceBridge
from experience.learning_signal import LearningSignalCollector
from experience.safe_learning_control import SafeLearningControl
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "learning.db")
    )


def make_learning_signals():
    collector = LearningSignalCollector()

    return [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
            metadata="task_family=parser",
        )
        for index in range(5)
    ]


def test_full_controlled_learning_flow(tmp_path):
    signals = make_learning_signals()

    unified = UnifiedLearningRouter()

    routing = unified.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        baseline_score_by_strategy={"property": 70.0},
        learned_score_by_strategy={"property": 95.0},
    )

    assert routing.repair.strategy == "property"
    assert routing.repair.learned is True
    assert routing.verification.strategy == "property"
    assert routing.verification.learned is True

    safe = SafeLearningControl()

    control = safe.evaluate(
        strategy="property",
        signals=signals,
        task_family="parser",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert control.allowed is True
    assert control.rollback is False
    assert len(control.signals) == 5

    persistence = ControlledLearningPersistence(
        LearningPersistenceBridge(make_store(tmp_path)),
    )

    persisted = persistence.persist(
        signals=signals,
        strategy="property",
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert persisted.allowed is True
    assert persisted.rollback is False
    assert persisted.persistence is not None
    assert persisted.persistence.persisted == 5


def test_high_regression_is_blocked_before_persistence(tmp_path):
    signals = make_learning_signals()

    store = make_store(tmp_path)

    persistence = ControlledLearningPersistence(
        LearningPersistenceBridge(store),
    )

    result = persistence.persist(
        signals=signals,
        strategy="property",
        baseline_score=95.0,
        learned_score=35.0,
    )

    assert isinstance(result, ControlledPersistenceResult)
    assert result.allowed is False
    assert result.rollback is True
    assert result.persistence is None
    assert store.recent(limit=20) == []


def test_cross_task_safety_blocks_even_when_learning_improves():
    signals = make_learning_signals()

    safe = SafeLearningControl()

    result = safe.evaluate(
        strategy="property",
        signals=signals,
        task_family="database",
        allow_cross_task=True,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert result.allowed is False
    assert result.rollback is False
    assert result.signals == ()
    assert "learning safety blocked" in result.reason


def test_control_adapter_and_safe_control_agree_on_regression():
    signals = make_learning_signals()

    adapter_result = LearningControlAdapter().evaluate(
        strategy="property",
        baseline_score=95.0,
        learned_score=35.0,
    )

    safe_result = SafeLearningControl().evaluate(
        strategy="property",
        signals=signals,
        task_family="parser",
        allow_cross_task=True,
        baseline_score=95.0,
        learned_score=35.0,
    )

    assert adapter_result.allowed is False
    assert adapter_result.rollback is True

    assert safe_result.allowed is False
    assert safe_result.rollback is True
    assert safe_result.severity == adapter_result.severity


def test_benchmark_is_green():
    benchmark = LearningControlBenchmark()

    assert benchmark.all_passed() is True


def test_complete_pipeline_is_deterministic(tmp_path):
    signals = make_learning_signals()

    def run():
        store = make_store(tmp_path)

        persistence = ControlledLearningPersistence(
            LearningPersistenceBridge(store),
        )

        return persistence.persist(
            signals=signals,
            strategy="property",
            baseline_score=70.0,
            learned_score=95.0,
        )

    first = run()
    second = run()

    assert first.allowed is True
    assert second.allowed is True
    assert first.persistence is not None
    assert second.persistence is not None
    assert first.persistence.experience_ids == second.persistence.experience_ids
    assert first.persistence.persisted == 5
    assert first.persistence.skipped == 0
    assert second.persistence.persisted == 0
    assert second.persistence.skipped == 5


def test_full_rollback_path_is_deterministic():
    signals = make_learning_signals()

    controller = SafeLearningControl()

    first = controller.evaluate(
        strategy="property",
        signals=signals,
        task_family="parser",
        allow_cross_task=True,
        baseline_score=95.0,
        learned_score=35.0,
    )

    second = controller.evaluate(
        strategy="property",
        signals=signals,
        task_family="parser",
        allow_cross_task=True,
        baseline_score=95.0,
        learned_score=35.0,
    )

    assert first == second


def test_empty_learning_history_never_becomes_usable():
    router = UnifiedLearningRouter()

    result = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="property",
        signals=[],
    )

    assert result.repair.strategy == "standard"
    assert result.repair.learned is False
    assert result.verification.strategy == "property"
    assert result.verification.learned is False
