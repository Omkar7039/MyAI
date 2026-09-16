from __future__ import annotations

from experience.adaptive_strategy import AdaptiveStrategyRanker
from experience.learning_approval import LearningApprovalPolicy
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_history import (
    LearningChangeHistory,
)
from experience.learning_change_proposal import (
    LearningChangeProposalBuilder,
)
from experience.learning_change_validator import (
    LearningChangeProposalValidator,
)
from experience.learning_control import LearningControlAdapter
from experience.learning_control_persistence import (
    ControlledLearningPersistence,
)
from experience.learning_effectiveness import (
    LearningEffectivenessEvaluator,
)
from experience.learning_governance import (
    LearningGovernanceController,
)
from experience.learning_persistence import LearningPersistenceBridge
from experience.learning_regression import LearningRegressionDetector
from experience.learning_safety import LearningSafetyGuard
from experience.learning_signal import LearningSignalCollector
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "full-governance.db")
    )


def make_evidence():
    collector = LearningSignalCollector()

    signals = [
        collector.repair_success(
            f"parser-{index}",
            strategy="property",
            score=95.0,
            metadata="task_family=parser",
        )
        for index in range(5)
    ]

    return signals


def make_candidate(signals):
    return AdaptiveStrategyRanker().best(
        signals,
        utility_by_strategy={"property": 95.0},
    )


def make_proposal(candidate, baseline=70.0, learned=100.0):
    effectiveness = LearningEffectivenessEvaluator().evaluate(
        baseline_score=baseline,
        learned_score=learned,
    )

    regression = LearningRegressionDetector().detect(
        strategy=candidate.strategy,
        baseline_score=baseline,
        learned_score=learned,
    )

    return LearningChangeProposalBuilder().build(
        candidate=candidate,
        effectiveness=effectiveness,
        regression=regression,
    )


def test_full_governed_adoption_flow(tmp_path):
    signals = make_evidence()
    candidate = make_candidate(signals)

    safety = LearningSafetyGuard().filter(
        task_family="parser",
        signals=signals,
        allow_cross_task=True,
    )

    assert safety.allowed is True

    control = LearningControlAdapter().evaluate(
        strategy=candidate.strategy,
        baseline_score=70.0,
        learned_score=100.0,
    )

    assert control.allowed is True
    assert control.rollback is False

    proposal = make_proposal(candidate)

    validator = LearningChangeProposalValidator()
    validation = validator.validate(proposal)

    assert validation.valid is True

    approval = LearningApprovalPolicy().decide(proposal)

    assert approval.approved is True

    application = LearningChangeApplication()

    applied = application.apply(
        proposal=proposal,
        approval=approval,
    )

    assert applied.strategy == "property"
    assert applied.applied_score == 100.0

    history = LearningChangeHistory(make_store(tmp_path))

    recorded = history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    assert recorded.persisted is True

    loaded = history.get(recorded.experience_id)

    assert loaded is not None
    assert loaded.category == "learning_change"


def test_governance_controller_matches_manual_pipeline():
    signals = make_evidence()
    candidate = make_candidate(signals)
    proposal = make_proposal(candidate)

    controller = LearningGovernanceController()

    result = controller.evaluate(proposal)

    assert result.approved is True
    assert result.applied is True
    assert result.change is not None
    assert result.strategy == "property"


def test_rejected_proposal_does_not_modify_application():
    signals = make_evidence()
    candidate = make_candidate(signals)

    proposal = make_proposal(
        candidate,
        baseline=80.0,
        learned=80.0,
    )

    controller = LearningGovernanceController()

    result = controller.evaluate(proposal)

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert controller.all_applied() == ()


def test_regressed_learning_is_blocked_before_application():
    signals = make_evidence()
    candidate = make_candidate(signals)

    control = LearningControlAdapter().evaluate(
        strategy=candidate.strategy,
        baseline_score=95.0,
        learned_score=35.0,
    )

    assert control.allowed is False
    assert control.rollback is True

    proposal = make_proposal(
        candidate,
        baseline=95.0,
        learned=35.0,
    )

    controller = LearningGovernanceController()
    result = controller.evaluate(proposal)

    assert result.approved is False
    assert result.applied is False


def test_cross_task_safety_blocks_before_control_acceptance():
    signals = make_evidence()

    safety = LearningSafetyGuard().filter(
        task_family="database",
        signals=signals,
        allow_cross_task=True,
    )

    assert safety.allowed is False
    assert safety.signals == ()


def test_applied_change_can_be_rolled_back():
    signals = make_evidence()
    candidate = make_candidate(signals)
    proposal = make_proposal(candidate)

    application = LearningChangeApplication()
    approval = LearningApprovalPolicy().decide(proposal)

    applied = application.apply(
        proposal=proposal,
        approval=approval,
    )

    assert application.get("property") is not None

    restored = application.rollback("property")

    assert restored is None
    assert application.get("property") is None


def test_learning_observations_and_governance_history_remain_separate(
    tmp_path,
):
    signals = make_evidence()
    store = make_store(tmp_path)

    observations = LearningPersistenceBridge(store).persist(
        signals
    )

    assert observations.persisted == 5

    history = LearningChangeHistory(store)

    assert history.recent() == []


def test_controlled_persistence_rejects_high_regression(tmp_path):
    signals = make_evidence()

    result = ControlledLearningPersistence(
        LearningPersistenceBridge(make_store(tmp_path)),
    ).persist(
        signals=signals,
        strategy="property",
        baseline_score=95.0,
        learned_score=35.0,
    )

    assert result.allowed is False
    assert result.rollback is True
    assert result.persistence is None


def test_full_pipeline_is_deterministic():
    signals = make_evidence()
    candidate = make_candidate(signals)

    proposal = make_proposal(candidate)

    first = LearningGovernanceController().evaluate(
        proposal
    )
    second = LearningGovernanceController().evaluate(
        proposal
    )

    assert first == second


def test_final_governance_state_is_sorted():
    signals = make_evidence()
    candidate = make_candidate(signals)

    controller = LearningGovernanceController()

    controller.evaluate(make_proposal(candidate))

    second_proposal = make_proposal(
        candidate,
        baseline=100.0,
        learned=100.0,
    )

    result = controller.evaluate(second_proposal)

    assert result.applied is False
    assert tuple(
        item.strategy
        for item in controller.all_applied()
    ) == ("property",)
