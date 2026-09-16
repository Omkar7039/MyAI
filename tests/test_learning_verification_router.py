from experience.learning_signal import LearningSignalCollector
from verification.learning_verification_router import (
    LearningAwareVerificationRouter,
)


def test_strong_history_selects_property_verification():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    result = LearningAwareVerificationRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.confidence > 0.0


def test_insufficient_history_uses_default():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            "verify",
            strategy="property",
            score=100.0,
        ),
    ]

    result = LearningAwareVerificationRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 100.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "insufficient historical observations" in result.reason


def test_mutation_can_be_learned():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="mutation",
            score=95.0,
        )
        for index in range(4)
    ]

    result = LearningAwareVerificationRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"mutation": 95.0},
    )

    assert result.strategy == "mutation"
    assert result.learned is True


def test_low_history_quality_falls_back():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            "a",
            strategy="standard",
            score=60.0,
        ),
        collector.verification_failure(
            "b",
            strategy="standard",
            score=0.0,
        ),
        collector.verification_failure(
            "c",
            strategy="standard",
            score=0.0,
        ),
    ]

    result = LearningAwareVerificationRouter().route(
        default_strategy="property",
        signals=signals,
        utility_by_strategy={"standard": 10.0},
    )

    assert result.strategy == "property"
    assert result.learned is False


def test_no_history_uses_default():
    result = LearningAwareVerificationRouter().route(
        default_strategy="mutation",
        signals=[],
    )

    assert result.strategy == "mutation"
    assert result.learned is False
    assert result.confidence == 0.0


def test_custom_router_is_respected():
    from experience.learning_router import LearningAwareStrategyRouter

    class FixedRouter(LearningAwareStrategyRouter):
        def route(
            self,
            *,
            default_strategy,
            signals,
            utility_by_strategy=None,
        ):
            from experience.learning_router import (
                LearningRouteDecision,
            )

            return LearningRouteDecision(
                strategy="property",
                learned=True,
                confidence=88.0,
                reason="test router",
            )

    result = LearningAwareVerificationRouter(
        router=FixedRouter(),
    ).route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.confidence == 88.0
    assert result.reason == "test router"


def test_empty_default_is_rejected_by_underlying_router():
    try:
        LearningAwareVerificationRouter().route(
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
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareVerificationRouter()

    first = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )
    second = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert first == second


def test_learning_control_allows_improved_verification_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareVerificationRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 70.0},
        learned_score_by_strategy={"property": 92.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert "learning control" in result.reason


def test_learning_control_blocks_regressed_verification_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareVerificationRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 90.0},
        learned_score_by_strategy={"property": 40.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "learning control blocked" in result.reason


def test_learning_control_is_skipped_without_score_maps():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=92.0,
        )
        for index in range(5)
    ]

    router = LearningAwareVerificationRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert result.strategy == "property"
    assert result.learned is True


def test_custom_control_threshold_is_respected():
    from experience.continuous_learning import ContinuousLearningController
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="property",
            score=92.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter(
        ContinuousLearningController(
            rollback_severity="medium",
        )
    )

    router = LearningAwareVerificationRouter(control=control)

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 90.0},
        learned_score_by_strategy={"property": 70.0},
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
        ):
            return LearningRouteDecision(
                strategy="property",
                learned=True,
                confidence=88.0,
                reason="test router",
            )

    result = LearningAwareVerificationRouter(
        router=FixedRouter(),
    ).route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.confidence == 88.0
    assert result.reason == "test router"
