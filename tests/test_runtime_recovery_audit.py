import pytest

from core.runtime_failure import RuntimeFailureClassifier
from core.runtime_recovery import RuntimeRecoveryDecisionEngine
from core.runtime_recovery_audit import (
    RuntimeRecoveryAudit,
    RuntimeRecoveryAuditEntry,
)
from core.runtime_recovery_guard import RuntimeRecoveryGuard


def make_audit(tmp_path):
    return RuntimeRecoveryAudit(
        tmp_path / "recovery_audit.db"
    )


def test_audit_store_starts_empty(tmp_path):
    audit = make_audit(tmp_path)

    assert audit.count() == 0
    assert audit.recent() == ()
    assert audit.schema_version() == 1


def test_record_creates_persistent_entry(tmp_path):
    audit = make_audit(tmp_path)

    entry = audit.record(
        fingerprint="state:learning",
        category="state",
        action="recover",
        allowed=False,
        attempts=1,
        reason="recovery required",
    )

    assert isinstance(entry, RuntimeRecoveryAuditEntry)
    assert entry.entry_id == 1
    assert entry.fingerprint == "state:learning"
    assert entry.category == "state"
    assert entry.action == "recover"
    assert entry.allowed is False
    assert entry.attempts == 1
    assert entry.reason == "recovery required"
    assert audit.count() == 1


def test_audit_survives_new_instance(tmp_path):
    path = tmp_path / "recovery_audit.db"

    first = RuntimeRecoveryAudit(path)

    first.record(
        fingerprint="runtime:startup",
        category="runtime",
        action="recover",
        allowed=False,
        attempts=1,
        reason="startup recovery required",
    )

    second = RuntimeRecoveryAudit(path)

    entries = second.recent()

    assert len(entries) == 1
    assert entries[0].fingerprint == "runtime:startup"


def test_recent_returns_newest_first(tmp_path):
    audit = make_audit(tmp_path)

    audit.record(
        fingerprint="first",
        category="timeout",
        action="retry",
        allowed=False,
        attempts=0,
        reason="first",
    )

    audit.record(
        fingerprint="second",
        category="state",
        action="recover",
        allowed=False,
        attempts=1,
        reason="second",
    )

    entries = audit.recent()

    assert [entry.fingerprint for entry in entries] == [
        "second",
        "first",
    ]


def test_recent_limit_is_enforced(tmp_path):
    audit = make_audit(tmp_path)

    for index in range(5):
        audit.record(
            fingerprint=f"failure:{index}",
            category="unknown",
            action="stop",
            allowed=False,
            attempts=0,
            reason=f"failure {index}",
        )

    entries = audit.recent(limit=2)

    assert len(entries) == 2
    assert entries[0].fingerprint == "failure:4"
    assert entries[1].fingerprint == "failure:3"


def test_record_decision_captures_classification_and_decision(
    tmp_path,
):
    audit = make_audit(tmp_path)

    classifier = RuntimeFailureClassifier()
    decision_engine = RuntimeRecoveryDecisionEngine()

    classification = classifier.classify(
        timed_out=True,
    )
    decision = decision_engine.decide(
        classification,
    )

    entry = audit.record_decision(
        fingerprint="timeout:job",
        classification=classification,
        decision=decision,
    )

    assert entry.category == "timeout"
    assert entry.action == "retry"
    assert entry.allowed is False
    assert entry.attempts == 0


def test_record_guard_captures_guard_result(tmp_path):
    audit = make_audit(tmp_path)

    classification = RuntimeFailureClassifier().classify(
        message="malformed state detected",
    )

    guard = RuntimeRecoveryGuard(
        max_attempts=1,
    )

    guard_result = guard.record(
        "state:learning",
    )

    entry = audit.record_guard(
        fingerprint="state:learning",
        classification=classification,
        guard=guard_result,
    )

    assert entry.category == "state"
    assert entry.action == "allow_recovery"
    assert entry.allowed is True
    assert entry.attempts == 1


def test_blocked_guard_is_audited(tmp_path):
    audit = make_audit(tmp_path)

    classification = RuntimeFailureClassifier().classify(
        message="malformed state detected",
    )

    guard = RuntimeRecoveryGuard(
        max_attempts=1,
    )

    guard.record("state:learning")
    blocked = guard.record("state:learning")

    entry = audit.record_guard(
        fingerprint="state:learning",
        classification=classification,
        guard=blocked,
    )

    assert entry.action == "block_recovery"
    assert entry.allowed is False
    assert entry.attempts == 1


def test_empty_fingerprint_is_rejected(tmp_path):
    audit = make_audit(tmp_path)

    with pytest.raises(
        ValueError,
        match="fingerprint must not be empty",
    ):
        audit.record(
            fingerprint=" ",
            category="state",
            action="recover",
            allowed=False,
            attempts=0,
            reason="invalid",
        )


def test_invalid_record_values_are_rejected(tmp_path):
    audit = make_audit(tmp_path)

    with pytest.raises(ValueError):
        audit.record(
            fingerprint="state",
            category="",
            action="recover",
            allowed=False,
            attempts=0,
            reason="invalid",
        )

    with pytest.raises(ValueError):
        audit.record(
            fingerprint="state",
            category="state",
            action="",
            allowed=False,
            attempts=0,
            reason="invalid",
        )

    with pytest.raises(ValueError):
        audit.record(
            fingerprint="state",
            category="state",
            action="recover",
            allowed=False,
            attempts=-1,
            reason="invalid",
        )

    with pytest.raises(ValueError):
        audit.record(
            fingerprint="state",
            category="state",
            action="recover",
            allowed=False,
            attempts=0,
            reason="",
        )


def test_recent_limit_must_be_positive(tmp_path):
    audit = make_audit(tmp_path)

    with pytest.raises(ValueError, match="limit must be > 0"):
        audit.recent(0)
