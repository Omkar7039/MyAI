from experience.learning_orchestrator import UnifiedLearningRouter
from experience.learning_signal import LearningSignalCollector


def test_strong_history_can_route_both_domains():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    result = UnifiedLearningRouter().route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
    )

    assert result.repair.strategy == "property"
    assert result.repair.learned is True
    assert result.verification.strategy == "property"
    assert result.verification.learned is True


def test_insufficient_history_preserves_both_defaults():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            "task",
            strategy="property",
            score=100.0,
        ),
    ]

    result = UnifiedLearningRouter().route(
        default_repair_strategy="standard",
        default_verification_strategy="mutation",
        signals=signals,
        utility_by_strategy={"property": 100.0},
    )

    assert result.repair.strategy == "standard"
    assert result.repair.learned is False
    assert result.verification.strategy == "mutation"
    assert result.verification.learned is False


def test_repair_and_verification_defaults_are_independent():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"repair-{index}",
            strategy="multifile",
            score=90.0,
        )
        for index in range(5)
    ]

    result = UnifiedLearningRouter().route(
        default_repair_strategy="standard",
        default_verification_strategy="property",
        signals=signals,
        utility_by_strategy={"multifile": 90.0},
    )

    assert result.repair.strategy == "multifile"
    assert result.repair.learned is True
    assert result.verification.strategy == "multifile"
    assert result.verification.learned is True


def test_empty_history_uses_all_defaults():
    result = UnifiedLearningRouter().route(
        default_repair_strategy="standard",
        default_verification_strategy="mutation",
        signals=[],
    )

    assert result.repair.strategy == "standard"
    assert result.repair.learned is False
    assert result.verification.strategy == "mutation"
    assert result.verification.learned is False


def test_custom_routers_are_respected():
    from experience.learning_router import LearningAwareStrategyRouter
    from experience.learning_router import LearningRouteDecision

    class FixedRouter(LearningAwareStrategyRouter):
        def __init__(self, strategy):
            super().__init__()
            self.strategy = strategy

        def route(
            self,
            *,
            default_strategy,
            signals,
            utility_by_strategy=None,
        ):
            return LearningRouteDecision(
                strategy=self.strategy,
                learned=True,
                confidence=88.0,
                reason="custom router",
            )

    repair_router = __import__(
        "experience.learning_repair_router",
        fromlist=["LearningAwareRepairRouter"],
    ).LearningAwareRepairRouter(
        router=FixedRouter("multifile")
    )

    verification_router = __import__(
        "verification.learning_verification_router",
        fromlist=["LearningAwareVerificationRouter"],
    ).LearningAwareVerificationRouter(
        router=FixedRouter("property")
    )

    result = UnifiedLearningRouter(
        repair_router=repair_router,
        verification_router=verification_router,
    ).route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=[],
    )

    assert result.repair.strategy == "multifile"
    assert result.verification.strategy == "property"
    assert result.repair.learned is True
    assert result.verification.learned is True


def test_empty_repair_default_is_rejected():
    try:
        UnifiedLearningRouter().route(
            default_repair_strategy="   ",
            default_verification_strategy="standard",
            signals=[],
        )
    except ValueError as exc:
        assert str(exc) == "default_strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_empty_verification_default_is_rejected():
    try:
        UnifiedLearningRouter().route(
            default_repair_strategy="standard",
            default_verification_strategy="   ",
            signals=[],
        )
    except ValueError as exc:
        assert str(exc) == "default_strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_routing_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = UnifiedLearningRouter()

    first = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )
    second = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert first == second


def test_unified_control_allows_improved_strategy_for_both_domains():
    from experience.learning_control import LearningControlAdapter

    from experience.learning_repair_router import LearningAwareRepairRouter
    from verification.learning_verification_router import (
        LearningAwareVerificationRouter,
    )

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter()

    router = UnifiedLearningRouter(
        repair_router=LearningAwareRepairRouter(control=control),
        verification_router=LearningAwareVerificationRouter(
            control=control
        ),
    )

    result = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        baseline_score_by_strategy={"property": 70.0},
        learned_score_by_strategy={"property": 95.0},
    )

    assert result.repair.strategy == "property"
    assert result.repair.learned is True
    assert result.verification.strategy == "property"
    assert result.verification.learned is True


def test_unified_control_blocks_regressed_strategy_for_both_domains():
    from experience.learning_control import LearningControlAdapter

    from experience.learning_repair_router import LearningAwareRepairRouter
    from verification.learning_verification_router import (
        LearningAwareVerificationRouter,
    )

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter()

    router = UnifiedLearningRouter(
        repair_router=LearningAwareRepairRouter(control=control),
        verification_router=LearningAwareVerificationRouter(
            control=control
        ),
    )

    result = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="mutation",
        signals=signals,
        utility_by_strategy={"property": 95.0},
        baseline_score_by_strategy={"property": 95.0},
        learned_score_by_strategy={"property": 40.0},
    )

    assert result.repair.strategy == "standard"
    assert result.repair.learned is False
    assert result.verification.strategy == "mutation"
    assert result.verification.learned is False


def test_unified_control_remains_backward_compatible_without_scores():
    from experience.learning_control import LearningControlAdapter

    from experience.learning_repair_router import LearningAwareRepairRouter
    from verification.learning_verification_router import (
        LearningAwareVerificationRouter,
    )

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter()

    router = UnifiedLearningRouter(
        repair_router=LearningAwareRepairRouter(control=control),
        verification_router=LearningAwareVerificationRouter(
            control=control
        ),
    )

    result = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="mutation",
        signals=signals,
        utility_by_strategy={"property": 95.0},
    )

    assert result.repair.strategy == "property"
    assert result.repair.learned is True
    assert result.verification.strategy == "property"
    assert result.verification.learned is True
