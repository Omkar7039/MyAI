from __future__ import annotations

import pytest

from experience.learning_change_proposal import (
    LearningChangeProposal,
)
from experience.learning_change_validator import (
    LearningChangeProposalValidator,
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
        "confidence": 40.0,
        "rationale": "learned strategy improved by 20.00 points",
    }

    values.update(overrides)

    return LearningChangeProposal(**values)


def test_valid_improvement_proposal():
    result = LearningChangeProposalValidator().validate(
        make_proposal()
    )

    assert result.valid is True
    assert result.reason == (
        "learning change proposal is structurally valid"
    )


def test_valid_neutral_proposal():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            current_score=80.0,
            proposed_score=80.0,
            improvement=0.0,
            improved=False,
        )
    )

    assert result.valid is True


def test_valid_regression_proposal():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            current_score=90.0,
            proposed_score=60.0,
            improvement=-30.0,
            improved=False,
            regression_detected=True,
            regression_severity="high",
        )
    )

    assert result.valid is True


def test_empty_strategy_is_rejected():
    result = LearningChangeProposalValidator().validate(
        make_proposal(strategy=" ")
    )

    assert result.valid is False
    assert result.reason == "strategy must not be empty"


@pytest.mark.parametrize(
    "score_field",
    ["current_score", "proposed_score"],
)
def test_scores_must_be_in_range(score_field):
    values = {
        "current_score": 70.0,
        "proposed_score": 90.0,
    }
    values[score_field] = 101.0

    result = LearningChangeProposalValidator().validate(
        make_proposal(**values)
    )

    assert result.valid is False
    assert score_field in result.reason


def test_zero_observations_are_rejected():
    result = LearningChangeProposalValidator().validate(
        make_proposal(observations=0)
    )

    assert result.valid is False
    assert result.reason == "observations must be at least 1"


def test_negative_observations_are_rejected():
    result = LearningChangeProposalValidator().validate(
        make_proposal(observations=-1)
    )

    assert result.valid is False
    assert result.reason == "observations must be at least 1"


def test_improvement_must_match_scores():
    result = LearningChangeProposalValidator().validate(
        make_proposal(improvement=10.0)
    )

    assert result.valid is False
    assert "improvement does not match" in result.reason


def test_confidence_must_be_in_range():
    result = LearningChangeProposalValidator().validate(
        make_proposal(confidence=101.0)
    )

    assert result.valid is False
    assert result.reason == (
        "confidence must be between 0 and 100"
    )


def test_detected_regression_cannot_have_none_severity():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            current_score=90.0,
            proposed_score=70.0,
            improvement=-20.0,
            improved=False,
            regression_detected=True,
            regression_severity="none",
        )
    )

    assert result.valid is False
    assert "severity cannot be none" in result.reason


def test_detected_regression_requires_negative_improvement():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            current_score=90.0,
            proposed_score=95.0,
            improvement=5.0,
            improved=True,
            regression_detected=True,
            regression_severity="low",
        )
    )

    assert result.valid is False
    assert "negative improvement" in result.reason


def test_non_regression_requires_none_severity():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            regression_detected=False,
            regression_severity="low",
        )
    )

    assert result.valid is False
    assert "severity must be none" in result.reason


def test_non_regression_cannot_have_negative_improvement():
    result = LearningChangeProposalValidator().validate(
        make_proposal(
            current_score=90.0,
            proposed_score=70.0,
            improvement=-20.0,
            improved=False,
            regression_detected=False,
            regression_severity="none",
        )
    )

    assert result.valid is False
    assert "negative improvement" in result.reason


def test_validator_is_deterministic():
    proposal = make_proposal()
    validator = LearningChangeProposalValidator()

    first = validator.validate(proposal)
    second = validator.validate(proposal)

    assert first == second
