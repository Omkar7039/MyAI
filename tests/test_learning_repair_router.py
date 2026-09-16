from experience.learning_signal import LearningSignalCollector
from experience.learning_repair_router import (
    LearningAwareRepairRouter,
)


def test_strong_history_selects_learned_repair_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=92.0,
        )
        for index in range(5)
    ]

    result = LearningAwareRepairRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
    )

    assert result.strategy == "multifile"
    assert result.learned is True
    assert result.confidence > 0.0


def test_insufficient_history_uses_default():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "repair",
            strategy="multifile",
            score=100.0,
        ),
    ]

    result = LearningAwareRepairRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 100.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "insufficient historical observations" in result.reason


def test_low_quality_history_falls_back():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "a",
            strategy="standard",
            score=60.0,
        ),
        collector.repair_failure(
            "b",
            strategy="standard",
            score=0.0,
        ),
        collector.repair_failure(
            "c",
            strategy="standard",
            score=0.0,
        ),
    ]

    result = LearningAwareRepairRouter().route(
        default_strategy="multifile",
        signals=signals,
        utility_by_strategy={"standard": 10.0},
    )

    assert result.strategy == "multifile"
    assert result.learned is False


def test_no_history_uses_default():
    result = LearningAwareRepairRouter().route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.confidence == 0.0


def test_learned_property_strategy_can_be_selected():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(4)
    ]

    result = LearningAwareRepairRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
    )

    assert result.strategy == "property"
    assert result.learned is True


def test_custom_router_is_respected():
    from experience.learning_router import LearningAwareStrategyRouter
    from experience.learning_router import LearningRouteDecision

    class FixedRouter(LearningAwareStrategyRouter):
        def route(
            self,
            *,
            default_strategy,
            signals,
            utility_by_strategy=None,
        ):
            return LearningRouteDecision(
                strategy="multifile",
                learned=True,
                confidence=91.0,
                reason="test router",
            )

    result = LearningAwareRepairRouter(
        router=FixedRouter(),
    ).route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "multifile"
    assert result.learned is True
    assert result.confidence == 91.0
    assert result.reason == "test router"


def test_empty_default_is_rejected():
    try:
        LearningAwareRepairRouter().route(
            default_strategy="   ",
            signals=[],
        )
    except ValueError as exc:
        assert str(exc) == "default_strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_result_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareRepairRouter()

    first = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
    )
    second = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
    )

    assert first == second


def test_learning_control_allows_improved_repair_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareRepairRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
        baseline_score_by_strategy={"multifile": 70.0},
        learned_score_by_strategy={"multifile": 92.0},
    )

    assert result.strategy == "multifile"
    assert result.learned is True
    assert "learning control" in result.reason


def test_learning_control_blocks_regressed_repair_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareRepairRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
        baseline_score_by_strategy={"multifile": 90.0},
        learned_score_by_strategy={"multifile": 40.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "learning control blocked" in result.reason


def test_learning_control_is_skipped_without_score_maps():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareRepairRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
    )

    assert result.strategy == "multifile"
    assert result.learned is True


def test_custom_control_threshold_is_respected():
    from experience.continuous_learning import ContinuousLearningController
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=92.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter(
        ContinuousLearningController(
            rollback_severity="medium",
        )
    )

    router = LearningAwareRepairRouter(control=control)

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
        baseline_score_by_strategy={"multifile": 90.0},
        learned_score_by_strategy={"multifile": 70.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_custom_router_remains_backward_compatible():
    from experience.learning_router import LearningAwareStrategyRouter
    from experience.learning_router import LearningRouteDecision

    class FixedRouter(LearningAwareStrategyRouter):
        def route(
            self,
            *,
            default_strategy,
            signals,
            utility_by_strategy=None,
            baseline_score_by_strategy=None,
            learned_score_by_strategy=None,
        ):
            return LearningRouteDecision(
                strategy="multifile",
                learned=True,
                confidence=91.0,
                reason="test router",
            )

    result = LearningAwareRepairRouter(
        router=FixedRouter(),
    ).route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "multifile"
    assert result.learned is True
    assert result.confidence == 91.0
    assert result.reason == "test router"
