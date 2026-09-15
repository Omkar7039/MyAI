from types import SimpleNamespace

from agents.debug_stop_policy import DebugStopPolicy


def test_initial_state_requests_investigation():
    decision = DebugStopPolicy().decide()

    assert decision.action == "investigate"


def test_verified_hypothesis_requests_repair():
    result = SimpleNamespace(selected=object())

    decision = DebugStopPolicy().decide(
        hypothesis_result=result,
    )

    assert decision.action == "repair"


def test_no_verified_hypothesis_stops_safely():
    result = SimpleNamespace(selected=None)

    decision = DebugStopPolicy().decide(
        hypothesis_result=result,
    )

    assert decision.action == "stop"
    assert "No hypothesis" in decision.reason


def test_successful_repair_requires_reinvestigation():
    result = SimpleNamespace(success=True)

    decision = DebugStopPolicy().decide(
        repair_result=result,
    )

    assert decision.action == "reinvestigate"


def test_failed_repair_requests_retry():
    result = SimpleNamespace(success=False)

    decision = DebugStopPolicy().decide(
        repair_result=result,
    )

    assert decision.action == "retry"


def test_resolved_reinvestigation_reports_success():
    result = SimpleNamespace(resolved=True)

    decision = DebugStopPolicy().decide(
        reinvestigation_result=result,
    )

    assert decision.action == "success"


def test_unresolved_reinvestigation_requests_retry():
    result = SimpleNamespace(resolved=False)

    decision = DebugStopPolicy().decide(
        reinvestigation_result=result,
    )

    assert decision.action == "retry"


def test_maximum_attempts_force_stop():
    decision = DebugStopPolicy().decide(
        attempt_count=3,
        max_attempts=3,
    )

    assert decision.action == "stop"
    assert "Maximum debugging attempts" in decision.reason


def test_attempt_limit_has_priority_over_retry():
    result = SimpleNamespace(resolved=False)

    decision = DebugStopPolicy().decide(
        reinvestigation_result=result,
        attempt_count=4,
        max_attempts=3,
    )

    assert decision.action == "stop"


def test_policy_is_deterministic():
    result = SimpleNamespace(selected=object())

    policy = DebugStopPolicy()

    first = policy.decide(hypothesis_result=result)
    second = policy.decide(hypothesis_result=result)

    assert first == second
