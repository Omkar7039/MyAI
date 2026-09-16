from __future__ import annotations

import pytest

from experience.learning_approval import LearningApprovalPolicy
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_proposal import (
    LearningChangeProposal,
)
from experience.learning_change_validator import (
    LearningChangeProposalValidator,
)
from experience.learning_governance import (
    LearningGovernanceController,
)


def make_proposal(**overrides):
    values = {
        "strategy": "property",
        "current_score": 70.0,
        "proposed_score": 90.0,
        "observations": 5,
        "improvement": 20.0,
        "improved": True,
        "regression_detected": False,
        "regression_severity": "none",
        "confidence": 80.0,
        "rationale": "learning improved",
    }

    values.update(overrides)

    return LearningChangeProposal(**values)


def test_valid_proposal_is_approved_and_applied():
    controller = LearningGovernanceController()

    result = controller.evaluate(make_proposal())

    assert result.approved is True
    assert result.applied is True
    assert result.strategy == "property"
    assert result.confidence == 80.0
    assert result.change is not None
    assert result.change.applied_score == 90.0


def test_invalid_proposal_is_rejected_before_application():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            improvement=999.0,
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert "validation failed" in result.reason
    assert controller.all_applied() == ()


def test_insufficient_observations_are_not_applied():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            observations=2,
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert "insufficient observations" in result.reason


def test_neutral_proposal_is_not_applied():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            current_score=80.0,
            proposed_score=80.0,
            improvement=0.0,
            improved=False,
            confidence=80.0,
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None


def test_low_confidence_proposal_is_not_applied():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            confidence=20.0,
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert "confidence" in result.reason


def test_regressed_proposal_is_not_applied():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            current_score=90.0,
            proposed_score=40.0,
            improvement=-50.0,
            improved=False,
            regression_detected=True,
            regression_severity="high",
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert controller.all_applied() == ()


def test_applied_state_can_be_retrieved():
    controller = LearningGovernanceController()

    controller.evaluate(make_proposal())

    result = controller.get_applied("property")

    assert result is not None
    assert result.strategy == "property"
    assert result.applied_score == 90.0


def test_multiple_strategies_are_retained():
    controller = LearningGovernanceController()

    controller.evaluate(
        make_proposal(
            strategy="property",
        )
    )

    controller.evaluate(
        make_proposal(
            strategy="mutation",
        )
    )

    applied = controller.all_applied()

    assert tuple(
        item.strategy
        for item in applied
    ) == ("mutation", "property")


def test_second_change_tracks_previous_state():
    controller = LearningGovernanceController()

    first = controller.evaluate(
        make_proposal(
            proposed_score=90.0,
            improvement=20.0,
        )
    )

    second = controller.evaluate(
        make_proposal(
            current_score=90.0,
            proposed_score=95.0,
            improvement=5.0,
            confidence=90.0,
        )
    )

    assert first.change is not None
    assert second.change is not None
    assert second.change.previous_score == 90.0
    assert second.change.applied_score == 95.0


def test_custom_components_are_respected():
    application = LearningChangeApplication()

    controller = LearningGovernanceController(
        validator=LearningChangeProposalValidator(),
        approval=LearningApprovalPolicy(
            min_confidence=10.0,
        ),
        application=application,
    )

    result = controller.evaluate(
        make_proposal(confidence=20.0)
    )

    assert result.approved is True
    assert result.applied is True
    assert application.get("property") is not None


def test_clear_removes_applied_state():
    controller = LearningGovernanceController()

    controller.evaluate(make_proposal())

    assert controller.all_applied()

    controller.clear()

    assert controller.all_applied() == ()
    assert controller.get_applied("property") is None


def test_missing_strategy_lookup_is_safe():
    controller = LearningGovernanceController()

    assert controller.get_applied("missing") is None


def test_governance_is_deterministic():
    proposal = make_proposal()

    first_controller = LearningGovernanceController()
    second_controller = LearningGovernanceController()

    first = first_controller.evaluate(proposal)
    second = second_controller.evaluate(proposal)

    assert first == second


def test_empty_strategy_is_rejected_by_validator():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(strategy=" ")
    )

    assert result.approved is False
    assert result.applied is False
    assert "strategy must not be empty" in result.reason


def test_application_dependency_is_reused():
    application = LearningChangeApplication()

    controller = LearningGovernanceController(
        application=application,
    )

    controller.evaluate(make_proposal())

    assert controller.get_applied("property") is application.get(
        "property"
    )


def test_validation_happens_before_approval():
    class RejectingValidator(LearningChangeProposalValidator):
        def validate(self, proposal):
            from experience.learning_change_validator import (
                LearningChangeValidation,
            )

            return LearningChangeValidation(
                valid=False,
                reason="forced validation rejection",
            )

    class TrackingApproval(LearningApprovalPolicy):
        def __init__(self):
            super().__init__()
            self.called = False

        def decide(self, proposal):
            self.called = True
            return super().decide(proposal)

    approval = TrackingApproval()

    controller = LearningGovernanceController(
        validator=RejectingValidator(),
        approval=approval,
    )

    result = controller.evaluate(make_proposal())

    assert result.approved is False
    assert result.applied is False
    assert approval.called is False


def test_approved_change_is_persisted_when_history_is_configured(
    tmp_path,
):
    from experience.learning_change_history import LearningChangeHistory
    from experience.store import ExperienceStore

    store = ExperienceStore(
        str(tmp_path / "governance-history.db")
    )
    history = LearningChangeHistory(store)

    controller = LearningGovernanceController(
        history=history,
    )

    result = controller.evaluate(
        make_proposal(
            proposed_score=100.0,
            improvement=30.0,
            confidence=80.0,
        )
    )

    assert result.approved is True
    assert result.applied is True
    assert result.change is not None

    records = history.recent()

    assert len(records) == 1
    assert records[0].category == "learning_change"
    assert records[0].action == "apply"
    assert records[0].success is True


def test_rejected_change_is_not_persisted(
    tmp_path,
):
    from experience.learning_change_history import LearningChangeHistory
    from experience.store import ExperienceStore

    store = ExperienceStore(
        str(tmp_path / "governance-history.db")
    )
    history = LearningChangeHistory(store)

    controller = LearningGovernanceController(
        history=history,
    )

    result = controller.evaluate(
        make_proposal(
            observations=2,
        )
    )

    assert result.approved is False
    assert result.applied is False
    assert result.change is None
    assert history.recent() == []


def test_existing_controller_without_history_remains_compatible():
    controller = LearningGovernanceController()

    result = controller.evaluate(
        make_proposal(
            proposed_score=100.0,
            improvement=30.0,
            confidence=80.0,
        )
    )

    assert result.approved is True
    assert result.applied is True
    assert result.change is not None
    assert controller.history is None


def test_history_persistence_is_idempotent(
    tmp_path,
):
    from experience.learning_change_history import LearningChangeHistory
    from experience.store import ExperienceStore

    store = ExperienceStore(
        str(tmp_path / "governance-history.db")
    )
    history = LearningChangeHistory(store)

    controller = LearningGovernanceController(
        history=history,
    )

    first = controller.evaluate(
        make_proposal(
            proposed_score=100.0,
            improvement=30.0,
            confidence=80.0,
        )
    )

    # Record the identical applied change again explicitly.
    assert first.change is not None

    approval = controller.approval.decide(
        make_proposal(
            proposed_score=100.0,
            improvement=30.0,
            confidence=80.0,
        )
    )

    duplicate = history.record(
        proposal=make_proposal(
            proposed_score=100.0,
            improvement=30.0,
            confidence=80.0,
        ),
        approval=approval,
        applied=first.change,
    )

    assert duplicate.persisted is False
    assert len(history.recent()) == 1
