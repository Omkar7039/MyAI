from __future__ import annotations

import pytest

from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_history import LearningChangeHistory
from experience.learning_change_proposal import LearningChangeProposal
from experience.store import ExperienceStore


def make_store(tmp_path):
    return ExperienceStore(
        str(tmp_path / "history.db")
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
        "rationale": "improvement",
    }

    values.update(overrides)

    return LearningChangeProposal(**values)


def make_approval(
    *,
    approved=True,
    strategy="property",
    confidence=80.0,
):
    return LearningApprovalDecision(
        approved=approved,
        strategy=strategy,
        confidence=confidence,
        reason="approved",
    )


def make_applied(
    application,
    proposal,
    approval,
):
    return application.apply(
        proposal=proposal,
        approval=approval,
    )


def test_record_persists_applied_change(tmp_path):
    store = make_store(tmp_path)
    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    result = LearningChangeHistory(store).record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    assert result.persisted is True
    assert result.experience_id.startswith("learning-change-")

    loaded = store.get(result.experience_id)

    assert loaded is not None
    assert loaded.category == "learning_change"
    assert loaded.action == "apply"
    assert loaded.success is True
    assert loaded.outcome == "approved"


def test_duplicate_record_is_skipped(tmp_path):
    store = make_store(tmp_path)
    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    history = LearningChangeHistory(store)

    first = history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )
    second = history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    assert first.persisted is True
    assert second.persisted is False
    assert first.experience_id == second.experience_id


def test_rejected_change_cannot_be_recorded(tmp_path):
    store = make_store(tmp_path)
    proposal = make_proposal()
    approval = make_approval(approved=False)

    application = LearningChangeApplication()

    with pytest.raises(
        ValueError,
        match="unapproved",
    ):
        LearningChangeHistory(store).record(
            proposal=proposal,
            approval=approval,
            applied=application._state.get("property"),
        )


def test_proposal_and_applied_strategy_must_match(tmp_path):
    store = make_store(tmp_path)
    proposal = make_proposal(strategy="property")
    approval = make_approval(strategy="property")

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    mismatched = make_proposal(strategy="mutation")

    with pytest.raises(
        ValueError,
        match="strategies must match",
    ):
        LearningChangeHistory(store).record(
            proposal=mismatched,
            approval=approval,
            applied=applied,
        )


def test_approval_and_applied_strategy_must_match(tmp_path):
    store = make_store(tmp_path)
    proposal = make_proposal(strategy="property")
    approval = make_approval(strategy="property")

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    mismatched_approval = make_approval(
        strategy="mutation",
    )

    with pytest.raises(
        ValueError,
        match="approval and applied",
    ):
        LearningChangeHistory(store).record(
            proposal=proposal,
            approval=mismatched_approval,
            applied=applied,
        )


def test_recent_returns_only_change_history(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)

    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    assert len(history.recent()) == 1
    assert history.recent()[0].category == "learning_change"


def test_get_returns_only_change_history(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)

    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    recorded = history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    loaded = history.get(recorded.experience_id)

    assert loaded is not None
    assert loaded.category == "learning_change"


def test_get_rejects_ordinary_experience(tmp_path):
    store = make_store(tmp_path)

    from experience.store import Experience

    experience = Experience(
        experience_id="ordinary",
        task="task",
        category="learning",
        action="repair_success",
        outcome="success",
        success=True,
        lesson="ordinary",
    )

    store.add(experience)

    history = LearningChangeHistory(store)

    assert history.get("ordinary") is None


def test_ids_are_deterministic(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)

    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    first = history._experience_id(
        proposal=proposal,
        applied=applied,
    )
    second = history._experience_id(
        proposal=proposal,
        applied=applied,
    )

    assert first == second


def test_history_metadata_contains_change_details(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)

    proposal = make_proposal()
    approval = make_approval()

    application = LearningChangeApplication()
    applied = make_applied(application, proposal, approval)

    recorded = history.record(
        proposal=proposal,
        approval=approval,
        applied=applied,
    )

    loaded = history.get(recorded.experience_id)

    assert loaded is not None
    assert "strategy=property" in loaded.metadata
    assert "applied_score=90.00" in loaded.metadata
    assert "observations=5" in loaded.metadata
    assert "improvement=20.00" in loaded.metadata


def test_history_isolated_from_ordinary_learning(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)

    from experience.store import Experience

    ordinary = Experience(
        experience_id="ordinary-learning",
        task="task",
        category="learning",
        action="repair_success",
        outcome="success",
        success=True,
        lesson="ordinary learning",
    )

    store.add(ordinary)

    assert history.recent() == []


def test_record_is_deterministic(tmp_path):
    proposal = make_proposal()
    approval = make_approval()

    first_store = make_store(tmp_path / "first")
    second_store = make_store(tmp_path / "second")

    first_application = LearningChangeApplication()
    second_application = LearningChangeApplication()

    first_applied = make_applied(
        first_application,
        proposal,
        approval,
    )
    second_applied = make_applied(
        second_application,
        proposal,
        approval,
    )

    first = LearningChangeHistory(first_store).record(
        proposal=proposal,
        approval=approval,
        applied=first_applied,
    )
    second = LearningChangeHistory(second_store).record(
        proposal=proposal,
        approval=approval,
        applied=second_applied,
    )

    assert first == second


def test_second_applied_change_has_previous_score(tmp_path):
    store = make_store(tmp_path)
    history = LearningChangeHistory(store)
    application = LearningChangeApplication()

    first_proposal = make_proposal()
    approval = make_approval()

    first = make_applied(
        application,
        first_proposal,
        approval,
    )

    history.record(
        proposal=first_proposal,
        approval=approval,
        applied=first,
    )

    second_proposal = make_proposal(
        current_score=90.0,
        proposed_score=95.0,
        improvement=5.0,
        confidence=90.0,
    )

    second = make_applied(
        application,
        second_proposal,
        make_approval(confidence=90.0),
    )

    result = history.record(
        proposal=second_proposal,
        approval=make_approval(confidence=90.0),
        applied=second,
    )

    loaded = history.get(result.experience_id)

    assert loaded is not None
    assert "previous_score=90.0" in loaded.metadata
    assert "applied_score=95.00" in loaded.metadata
