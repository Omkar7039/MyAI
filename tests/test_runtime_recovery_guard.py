import pytest

from core.runtime_recovery_guard import (
    RecoveryGuardResult,
    RuntimeRecoveryGuard,
)


def test_new_fingerprint_is_allowed():
    guard = RuntimeRecoveryGuard(max_attempts=3)

    result = guard.check("state:learning")

    assert isinstance(result, RecoveryGuardResult)
    assert result.allowed is True
    assert result.attempts == 0
    assert result.remaining == 3


def test_record_increments_attempt_count():
    guard = RuntimeRecoveryGuard(max_attempts=3)

    first = guard.record("state:learning")
    second = guard.record("state:learning")

    assert first.allowed is True
    assert first.attempts == 1
    assert first.remaining == 2

    assert second.allowed is True
    assert second.attempts == 2
    assert second.remaining == 1

    assert guard.attempts("state:learning") == 2


def test_attempt_limit_blocks_further_recovery():
    guard = RuntimeRecoveryGuard(max_attempts=2)

    guard.record("state:learning")
    guard.record("state:learning")

    result = guard.check("state:learning")

    assert result.allowed is False
    assert result.attempts == 2
    assert result.remaining == 0
    assert "limit reached" in result.reason


def test_record_cannot_exceed_limit():
    guard = RuntimeRecoveryGuard(max_attempts=1)

    first = guard.record("runtime:startup")
    second = guard.record("runtime:startup")

    assert first.allowed is True
    assert first.attempts == 1

    assert second.allowed is False
    assert second.attempts == 1
    assert second.remaining == 0


def test_different_failures_have_independent_limits():
    guard = RuntimeRecoveryGuard(max_attempts=1)

    guard.record("state:learning")

    state_result = guard.check("state:learning")
    runtime_result = guard.check("runtime:startup")

    assert state_result.allowed is False
    assert runtime_result.allowed is True


def test_reset_allows_new_recovery_cycle():
    guard = RuntimeRecoveryGuard(max_attempts=1)

    guard.record("state:learning")
    assert guard.check("state:learning").allowed is False

    guard.reset("state:learning")

    result = guard.check("state:learning")

    assert result.allowed is True
    assert result.attempts == 0
    assert result.remaining == 1


def test_clear_removes_all_attempt_history():
    guard = RuntimeRecoveryGuard(max_attempts=2)

    guard.record("state:learning")
    guard.record("runtime:startup")

    guard.clear()

    assert guard.attempts("state:learning") == 0
    assert guard.attempts("runtime:startup") == 0


def test_zero_attempt_limit_disables_automatic_recovery():
    guard = RuntimeRecoveryGuard(max_attempts=0)

    result = guard.check("state:learning")

    assert result.allowed is False
    assert result.attempts == 0
    assert result.remaining == 0


def test_empty_fingerprint_is_rejected():
    guard = RuntimeRecoveryGuard(max_attempts=3)

    with pytest.raises(ValueError, match="fingerprint must not be empty"):
        guard.check("   ")


def test_empty_fingerprint_is_rejected_for_record_reset_and_attempts():
    guard = RuntimeRecoveryGuard(max_attempts=3)

    with pytest.raises(ValueError):
        guard.record("")

    with pytest.raises(ValueError):
        guard.reset(" ")

    with pytest.raises(ValueError):
        guard.attempts("\t")


def test_fingerprints_are_whitespace_normalized():
    guard = RuntimeRecoveryGuard(max_attempts=1)

    guard.record("  state:learning  ")

    result = guard.check("state:learning")

    assert result.allowed is False
    assert result.attempts == 1


def test_guard_is_deterministic_for_same_state():
    guard = RuntimeRecoveryGuard(max_attempts=2)

    first = guard.check("state:learning")
    second = guard.check("state:learning")

    assert first == second
