from core.orchestrator import Orchestrator
from experience.learning_signal import LearningSignalCollector


def test_orchestrator_has_learning_router():
    orchestrator = object.__new__(Orchestrator)

    from experience.learning_orchestrator import UnifiedLearningRouter

    orchestrator.learning_router = UnifiedLearningRouter()

    assert isinstance(
        orchestrator.learning_router,
        UnifiedLearningRouter,
    )


def test_learning_router_preserves_default_without_history():
    from experience.learning_orchestrator import UnifiedLearningRouter

    router = UnifiedLearningRouter()

    result = router.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=[],
    )

    assert result.repair.strategy == "standard"
    assert result.verification.strategy == "standard"
    assert result.repair.learned is False
    assert result.verification.learned is False


def test_orchestrator_learning_route_accepts_historical_signals():
    collector = LearningSignalCollector()
    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
        )
        for index in range(5)
    ]

    router = Orchestrator.__new__(Orchestrator)
    from experience.learning_orchestrator import UnifiedLearningRouter

    router.learning_router = UnifiedLearningRouter()

    result = router.learning_router.route(
        default_repair_strategy="standard",
        default_verification_strategy="standard",
        signals=signals,
        utility_by_strategy={"property": 95.0},
    )

    assert result.repair.strategy == "property"
    assert result.verification.strategy == "property"
    assert result.repair.learned is True
    assert result.verification.learned is True


def test_orchestrator_exposes_governed_learning_router():
    orchestrator = object.__new__(Orchestrator)

    from experience.governed_strategy_router import GovernedStrategyRouter

    orchestrator.governed_learning_router = GovernedStrategyRouter()

    assert isinstance(
        orchestrator.governed_learning_router,
        GovernedStrategyRouter,
    )


def test_governed_learning_router_can_accept_strong_history():
    from experience.governed_strategy_router import GovernedStrategyRouter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=100.0,
        )
        for index in range(5)
    ]

    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=signals,
        baseline_score=70.0,
        utility_by_strategy={"property": 100.0},
    )

    assert result.strategy == "property"
    assert result.learned is True
    assert result.governed is True


def test_governed_learning_router_falls_back_on_regression():
    from experience.governed_strategy_router import GovernedStrategyRouter

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=40.0,
        )
        for index in range(5)
    ]

    result = GovernedStrategyRouter().route(
        default_strategy="standard",
        signals=signals,
        baseline_score=100.0,
        utility_by_strategy={"property": 40.0},
    )

    assert result.strategy == "standard"
    assert result.learned is False


def test_orchestrator_handle_signature_remains_backward_compatible():
    orchestrator = object.__new__(Orchestrator)

    import inspect

    signature = inspect.signature(
        Orchestrator.handle
    )

    assert "learning_signals" in signature.parameters
    assert "utility_by_strategy" in signature.parameters
    assert "baseline_score_by_strategy" in signature.parameters
    assert "task_family" in signature.parameters
    assert "allow_cross_task" in signature.parameters


def test_governed_arguments_are_optional():
    import inspect

    signature = inspect.signature(
        Orchestrator.handle
    )

    assert (
        signature.parameters[
            "baseline_score_by_strategy"
        ].default is None
    )
    assert (
        signature.parameters[
            "task_family"
        ].default is None
    )
    assert (
        signature.parameters[
            "allow_cross_task"
        ].default is False
    )
