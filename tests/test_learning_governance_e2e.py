from __future__ import annotations

from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_history import (
    LearningChangeHistory,
)
from experience.learning_change_proposal import (
    LearningChangeProposalBuilder,
)
from experience.learning_control import LearningControlAdapter
from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)
from experience.learning_governance import (
    LearningGovernanceController,
)
from experience.learning_persistence import (
    LearningPersistenceBridge,
)
from experience.learning_regression import (
    LearningRegressionDetector,
)
from experience.learning_signal import (
    LearningSignalCollector,
)
from experience.learning_safety import (
    LearningSafetyGuard,
)
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "governance.db")
    )


def make_candidate():
    from experience.adaptive_strategy import AdaptiveStrategyRanker

    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"task-{index}",
            strategy="property",
            score=95.0,
            metadata="task_family=parser",
        )
        for index in range(5)
    ]

    candidate = AdaptiveStrategyRanker().best(
        signals,
        utility_by_strategy={"property": 95.0},
    )

    return signals, candidate


def test_full_governance_flow(tmp_path):
    signals, candidate = make_candidate()

    safety = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert safety.allowed is True
    assert len(safety.signals) == 5

    control = LearningControlAdapter().evaluate(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=95.0,
    )

    assert control.allowed is True
    assert control.rollback is False

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=70.0,
        learned_score=95.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=95.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    controller = LearningGovernanceController()

    governance = controller.evaluate(proposal)

    assert governance.approved is True
    assert governance.applied is True
    assert governance.change is not None
    assert governance.change.applied_score == 95.0

    history = LearningChangeHistory(
        make_store(tmp_path)
    )

    recorded = history.record(
        proposal=proposal,
        approval=controller.approval.decide(proposal),
        applied=governance.change,
    )

    assert recorded.persisted is True

    loaded = history.get(recorded.experience_id)

    assert loaded is not None
    assert loaded.category == "learning_change"
    assert loaded.success is True


def test_regression_is_blocked_before_governance_application(tmp_path):
    signals, candidate = make_candidate()

    control = LearningControlAdapter().evaluate(
        strategy=candidate.strategy,
        baseline_score=95.0,
        learned_score=40.0,
    )

    assert control.allowed is False
    assert control.rollback is True

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=95.0,
        learned_score=40.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=95.0,
        learned_score=40.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    governance = LearningGovernanceController().evaluate(
        proposal
    )

    assert governance.approved is False
    assert governance.applied is False
    assert governance.change is None


def test_cross_task_safety_blocks_governance_input():
    signals, _ = make_candidate()

    safety = LearningSafetyGuard().filter(
        task_family="database",
        signals=signals,
        allow_cross_task=True,
    )

    assert safety.allowed is False
    assert safety.signals == ()


def test_rejected_governance_change_is_not_recorded(tmp_path):
    _, candidate = make_candidate()

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=80.0,
        learned_score=80.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=80.0,
        learned_score=80.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    controller = LearningGovernanceController()
    governance = controller.evaluate(proposal)

    assert governance.approved is False
    assert governance.applied is False

    store = make_store(tmp_path)

    history = LearningChangeHistory(store)

    assert history.recent() == []


def test_applied_change_can_be_rolled_back():
    _, candidate = make_candidate()

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=70.0,
        learned_score=100.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=100.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    controller = LearningGovernanceController()

    first = controller.evaluate(proposal)

    assert first.applied is True
    assert controller.get_applied("property") is not None

    restored = controller.application.rollback("property")

    assert restored is None
    assert controller.get_applied("property") is None


def test_duplicate_history_record_is_idempotent(tmp_path):
    _, candidate = make_candidate()

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=70.0,
        learned_score=100.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=100.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    controller = LearningGovernanceController()
    governance = controller.evaluate(proposal)

    approval = controller.approval.decide(proposal)

    history = LearningChangeHistory(
        make_store(tmp_path)
    )

    first = history.record(
        proposal=proposal,
        approval=approval,
        applied=governance.change,
    )

    second = history.record(
        proposal=proposal,
        approval=approval,
        applied=governance.change,
    )

    assert first.experience_id == second.experience_id
    assert first.persisted is True
    assert second.persisted is False


def test_learning_observation_persistence_is_separate_from_change_history(
    tmp_path,
):
    signals, _ = make_candidate()

    store = make_store(tmp_path)

    learning_result = LearningPersistenceBridge(store).persist(
        signals
    )

    assert learning_result.persisted == 5

    history = LearningChangeHistory(store)

    assert history.recent() == []


def test_governance_pipeline_is_deterministic():
    _, candidate = make_candidate()

    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=70.0,
        learned_score=100.0,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=100.0,
    )

    proposal = LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )

    first = LearningGovernanceController().evaluate(proposal)
    second = LearningGovernanceController().evaluate(proposal)

    assert first == second
