from core.runtime_recovery_audit import RuntimeRecoveryAudit
from core.runtime_recovery_controller import (
    RuntimeRecoveryController,
)
from core.runtime_recovery_guard import RuntimeRecoveryGuard
from core.runtime_recovery_throttle import RuntimeRecoveryThrottle


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def make_controller(tmp_path, *, max_attempts=3, cooldown=5):
    clock = FakeClock()

    audit = RuntimeRecoveryAudit(
        tmp_path / "recovery_audit.db"
    )

    return (
        RuntimeRecoveryController(
            guard=RuntimeRecoveryGuard(
                max_attempts=max_attempts
            ),
            throttle=RuntimeRecoveryThrottle(
                cooldown_seconds=cooldown,
                clock=clock,
            ),
            audit=audit,
        ),
        audit,
        clock,
    )


def test_timeout_flows_to_retry_and_is_audited(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    result = controller.handle(
        fingerprint="timeout:worker",
        timed_out=True,
    )

    assert result.action == "retry"
    assert result.recovered is False
    assert result.classification.category == "timeout"

    entries = audit.recent(limit=2)

    assert entries[0].action == "retry"
    assert entries[0].category == "timeout"


def test_state_failure_is_recovered_and_audited(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    calls = []

    def recover():
        calls.append(True)
        return True

    result = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=recover,
    )

    assert calls == [True]
    assert result.classification.category == "state"
    assert result.recovered is True
    assert result.action == "continue"

    actions = [
        entry.action
        for entry in reversed(audit.recent(limit=10))
    ]

    assert "recover" in actions
    assert "allow_recovery" in actions
    assert "recovery_success" in actions


def test_recovery_failure_stops_safely(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    result = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: False,
    )

    assert result.recovered is False
    assert result.action == "stop"
    assert "reported failure" in result.reason

    assert audit.recent(limit=1)[0].action == (
        "recovery_failed"
    )


def test_recovery_exception_stops_safely(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    def recover():
        raise RuntimeError("recovery exploded")

    result = controller.handle(
        fingerprint="runtime:startup",
        message="runtime startup failed",
        recover=recover,
    )

    assert result.recovered is False
    assert result.action == "stop"
    assert "recovery exploded" in result.reason

    assert audit.recent(limit=1)[0].action == (
        "recovery_failed"
    )


def test_guard_blocks_repeated_recovery(tmp_path):
    controller, audit, _ = make_controller(
        tmp_path,
        max_attempts=1,
        cooldown=0,
    )

    first = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    second = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    assert first.recovered is True
    assert second.recovered is False
    assert second.action == "stop"
    assert "limit" in second.reason

    assert audit.recent(limit=1)[0].action == (
        "block_recovery"
    )


def test_throttle_blocks_rapid_recovery(tmp_path):
    controller, audit, clock = make_controller(
        tmp_path,
        max_attempts=3,
        cooldown=5,
    )

    first = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    second = controller.handle(
        fingerprint="state:learning-2",
        message="malformed state detected",
        recover=lambda: True,
    )

    # First fingerprint proves normal recovery.
    assert first.recovered is True

    # Different fingerprint remains independently allowed.
    assert second.recovered is True

    clock.advance(1)

    third = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    assert third.recovered is False
    assert third.action == "stop"
    assert "cooldown" in third.reason

    assert audit.recent(limit=1)[0].action == (
        "cooldown_block"
    )


def test_recovery_allowed_after_cooldown(tmp_path):
    controller, audit, clock = make_controller(
        tmp_path,
        max_attempts=3,
        cooldown=5,
    )

    first = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    assert first.recovered is True

    clock.advance(5)

    second = controller.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    assert second.recovered is True
    assert second.action == "continue"


def test_unknown_failure_stops_without_recovery(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    calls = []

    result = controller.handle(
        fingerprint="unknown:failure",
        error=RuntimeError("unexpected failure"),
        recover=lambda: calls.append(True),
    )

    assert result.action == "stop"
    assert result.recovered is False
    assert calls == []

    assert audit.recent(limit=1)[0].action == "stop"


def test_no_failure_continues_without_recovery(tmp_path):
    controller, audit, _ = make_controller(tmp_path)

    calls = []

    result = controller.handle(
        fingerprint="none:test",
        recover=lambda: calls.append(True),
    )

    assert result.action == "continue"
    assert result.recovered is False
    assert calls == []

    assert audit.recent(limit=1)[0].action == "continue"


def test_controller_survives_new_instance_with_persistent_audit(
    tmp_path,
):
    audit_path = tmp_path / "recovery_audit.db"

    first_audit = RuntimeRecoveryAudit(audit_path)
    first = RuntimeRecoveryController(
        audit=first_audit,
        guard=RuntimeRecoveryGuard(max_attempts=3),
        throttle=RuntimeRecoveryThrottle(
            cooldown_seconds=0,
        ),
    )

    result = first.handle(
        fingerprint="state:learning",
        message="malformed state detected",
        recover=lambda: True,
    )

    assert result.recovered is True

    second_audit = RuntimeRecoveryAudit(audit_path)

    assert second_audit.count() >= 3

    actions = [
        entry.action
        for entry in second_audit.recent(limit=10)
    ]

    assert "recovery_success" in actions
