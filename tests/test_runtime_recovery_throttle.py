import pytest

from core.runtime_recovery_throttle import (
    RecoveryThrottleResult,
    RuntimeRecoveryThrottle,
)


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def test_new_fingerprint_is_allowed():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    result = throttle.check("state:learning")

    assert isinstance(result, RecoveryThrottleResult)
    assert result.allowed is True
    assert result.remaining == 0.0


def test_repeated_recovery_is_blocked_during_cooldown():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    throttle.record("state:learning")

    result = throttle.check("state:learning")

    assert result.allowed is False
    assert result.elapsed == 0.0
    assert result.remaining == 5.0
    assert "cooldown" in result.reason


def test_recovery_is_allowed_after_cooldown():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    throttle.record("state:learning")
    clock.advance(5)

    result = throttle.check("state:learning")

    assert result.allowed is True
    assert result.remaining == 0.0


def test_partial_cooldown_reports_remaining_time():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=10,
        clock=clock,
    )

    throttle.record("state:learning")
    clock.advance(3)

    result = throttle.check("state:learning")

    assert result.allowed is False
    assert result.elapsed == 3.0
    assert result.remaining == 7.0


def test_different_fingerprints_have_independent_cooldowns():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    throttle.record("state:learning")

    blocked = throttle.check("state:learning")
    allowed = throttle.check("runtime:startup")

    assert blocked.allowed is False
    assert allowed.allowed is True


def test_reset_removes_fingerprint_cooldown():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    throttle.record("state:learning")
    throttle.reset("state:learning")

    result = throttle.check("state:learning")

    assert result.allowed is True
    assert result.elapsed == 0.0


def test_clear_removes_all_cooldowns():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    throttle.record("state:learning")
    throttle.record("runtime:startup")

    throttle.clear()

    assert throttle.check("state:learning").allowed is True
    assert throttle.check("runtime:startup").allowed is True


def test_zero_cooldown_allows_immediate_recovery():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=0,
        clock=clock,
    )

    throttle.record("state:learning")

    result = throttle.check("state:learning")

    assert result.allowed is True
    assert result.remaining == 0.0


def test_negative_cooldown_is_rejected():
    with pytest.raises(
        ValueError,
        match="cooldown_seconds must be >= 0",
    ):
        RuntimeRecoveryThrottle(
            cooldown_seconds=-1,
        )


def test_empty_fingerprint_is_rejected():
    throttle = RuntimeRecoveryThrottle()

    with pytest.raises(
        ValueError,
        match="fingerprint must not be empty",
    ):
        throttle.check(" ")


def test_record_returns_remaining_cooldown():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=8,
        clock=clock,
    )

    result = throttle.record("state:learning")

    assert result.allowed is True
    assert result.remaining == 8.0


def test_last_attempt_is_available():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    assert throttle.last_attempt("state:learning") is None

    throttle.record("state:learning")

    assert throttle.last_attempt("state:learning") == 100.0


def test_throttle_is_deterministic_with_same_clock():
    clock = FakeClock()
    throttle = RuntimeRecoveryThrottle(
        cooldown_seconds=5,
        clock=clock,
    )

    first = throttle.check("state:learning")
    second = throttle.check("state:learning")

    assert first == second
