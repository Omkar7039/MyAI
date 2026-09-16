from experience.learning_router import LearningAwareStrategyRouter
from experience.learning_signal import LearningSignalCollector


def test_strong_history_selects_learned_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    result = LearningAwareStrategyRouter().route(
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
        collector.repair_success(
            "task",
            strategy="property",
            score=100.0,
        ),
    ]

    result = LearningAwareStrategyRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 100.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "insufficient historical observations" in result.reason


def test_low_quality_history_uses_default():
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

    result = LearningAwareStrategyRouter().route(
        default_strategy="property",
        signals=signals,
        utility_by_strategy={"standard": 20.0},
    )

    assert result.strategy == "property"
    assert result.learned is False


def test_no_history_uses_default():
    result = LearningAwareStrategyRouter().route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert result.confidence == 0.0


def test_default_strategy_is_trimmed():
    result = LearningAwareStrategyRouter().route(
        default_strategy="  standard  ",
        signals=[],
    )

    assert result.strategy == "standard"


def test_empty_default_strategy_is_rejected():
    try:
        LearningAwareStrategyRouter().route(
            default_strategy="   ",
            signals=[],
        )
    except ValueError as exc:
        assert str(exc) == "default_strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_learning_can_select_mutation_strategy():
    collector = LearningSignalCollector()

    signals = [
        collector.verification_success(
            f"verify-{index}",
            strategy="mutation",
            score=95.0,
        )
        for index in range(4)
    ]

    result = LearningAwareStrategyRouter().route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"mutation": 95.0},
    )

    assert result.strategy == "mutation"
    assert result.learned is True


def test_custom_policy_is_respected():
    from experience.learning_policy import LearningPolicy

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter(
        policy=LearningPolicy(
            min_observations=10,
        ),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_custom_ranker_is_respected():
    from experience.adaptive_strategy import AdaptiveStrategyRanker

    class EmptyRanker(AdaptiveStrategyRanker):
        def rank(self, signals, utility_by_strategy=None):
            return ()

    result = LearningAwareStrategyRouter(
        ranker=EmptyRanker(),
    ).route(
        default_strategy="standard",
        signals=[],
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_router_is_deterministic():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter()

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


def test_learning_control_allows_improved_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 70.0},
        learned_score_by_strategy={"property": 90.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert "learning control" in result.reason


def test_learning_control_blocks_high_regression():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter(
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
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert "learning policy" in result.reason


def test_learning_control_only_applies_to_selected_strategy():
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    router = LearningAwareStrategyRouter(
        control=LearningControlAdapter(),
    )

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"other": 90.0},
        learned_score_by_strategy={"other": 40.0},
    )

    assert result.strategy == "property"
    assert result.learned is True


def test_custom_control_can_change_rollback_threshold():
    from experience.continuous_learning import ContinuousLearningController
    from experience.learning_control import LearningControlAdapter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=90.0,
        )
        for index in range(5)
    ]

    control = LearningControlAdapter(
        ContinuousLearningController(
            rollback_severity="medium",
        )
    )

    router = LearningAwareStrategyRouter(control=control)

    result = router.route(
        default_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 90.0},
        baseline_score_by_strategy={"property": 90.0},
        learned_score_by_strategy={"property": 70.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False
    assert "learning control blocked" in result.reason
