from __future__ import annotations

import pytest

from experience.learning_approval import LearningApprovalPolicy
from experience.learning_change_proposal import (
    LearningChangeProposal,
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
        "rationale": "learned strategy improved by 20.00 points",
    }

    values.update(overrides)

    return LearningChangeProposal(**values)


def test_strong_proposal_is_approved():
    decision = LearningApprovalPolicy().decide(
        make_proposal()
    )

    assert decision.approved is True
    assert decision.strategy == "property"
    assert decision.confidence == 80.0


def test_insufficient_observations_are_rejected():
    decision = LearningApprovalPolicy().decide(
        make_proposal(observations=2)
    )

    assert decision.approved is False
    assert "insufficient observations" in decision.reason


def test_non_improving_proposal_is_rejected():
    decision = LearningApprovalPolicy().decide(
        make_proposal(
            current_score=80.0,
            proposed_score=80.0,
            improvement=0.0,
            improved=False,
            confidence=80.0,
        )
    )

    assert decision.approved is False
    assert "does not improve" in decision.reason


def test_improvement_threshold_is_respected():
    policy = LearningApprovalPolicy(
        min_improvement=10.0,
    )

    decision = policy.decide(
        make_proposal(
            current_score=70.0,
            proposed_score=75.0,
            improvement=5.0,
            confidence=80.0,
        )
    )

    assert decision.approved is False
    assert "below approval threshold" in decision.reason


def test_exact_improvement_threshold_is_approved():
    policy = LearningApprovalPolicy(
        min_improvement=20.0,
    )

    decision = policy.decide(
        make_proposal(
            improvement=20.0,
        )
    )

    assert decision.approved is True


def test_low_confidence_is_rejected():
    policy = LearningApprovalPolicy(
        min_confidence=50.0,
    )

    decision = policy.decide(
        make_proposal(
            confidence=49.0,
        )
    )

    assert decision.approved is False
    assert "confidence" in decision.reason


def test_exact_confidence_threshold_is_approved():
    policy = LearningApprovalPolicy(
        min_confidence=50.0,
    )

    decision = policy.decide(
        make_proposal(
            confidence=50.0,
        )
    )

    assert decision.approved is True


def test_regression_is_rejected():
    decision = LearningApprovalPolicy().decide(
        make_proposal(
            current_score=90.0,
            proposed_score=60.0,
            improvement=-30.0,
            improved=False,
            regression_detected=True,
            regression_severity="high",
        )
    )

    assert decision.approved is False


def test_invalid_proposal_is_rejected():
    decision = LearningApprovalPolicy().decide(
        make_proposal(
            improvement=999.0,
        )
    )

    assert decision.approved is False
    assert "validation failed" in decision.reason


def test_custom_observation_threshold():
    policy = LearningApprovalPolicy(
        min_observations=10,
    )

    decision = policy.decide(
        make_proposal(observations=10)
    )

    assert decision.approved is True


def test_invalid_configuration():
    with pytest.raises(ValueError):
        LearningApprovalPolicy(min_observations=0)

    with pytest.raises(ValueError):
        LearningApprovalPolicy(min_improvement=-1.0)

    with pytest.raises(ValueError):
        LearningApprovalPolicy(min_confidence=101.0)


def test_custom_validator_is_respected():
    from experience.learning_change_validator import (
        LearningChangeProposalValidator,
        LearningChangeValidation,
    )

    class RejectAllValidator(LearningChangeProposalValidator):
        def validate(self, proposal):
            return LearningChangeValidation(
                valid=False,
                reason="forced rejection",
            )

    policy = LearningApprovalPolicy(
        validator=RejectAllValidator(),
    )

    decision = policy.decide(make_proposal())

    assert decision.approved is False
    assert "forced rejection" in decision.reason


def test_approval_is_deterministic():
    proposal = make_proposal()
    policy = LearningApprovalPolicy()

    first = policy.decide(proposal)
    second = policy.decide(proposal)

    assert first == second


def test_strategy_is_preserved():
    decision = LearningApprovalPolicy().decide(
        make_proposal(strategy="mutation")
    )

    assert decision.strategy == "mutation"
