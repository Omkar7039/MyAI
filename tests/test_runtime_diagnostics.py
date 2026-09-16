from core.runtime_diagnostics import (
    RuntimeDiagnostics,
    RuntimeDiagnosticsChecker,
)
from core.runtime_state import RuntimeStateStore
from experience.learning_approval import LearningApprovalDecision
from experience.learning_change_application import (
    LearningChangeApplication,
)
from experience.learning_change_proposal import LearningChangeProposal
from experience.persistent_learning_state import (
    PersistentLearningState,
)


def make_proposal(
    *,
    strategy="property",
    current=70.0,
    proposed=100.0,
):
    return LearningChangeProposal(
        strategy=strategy,
        current_score=current,
        proposed_score=proposed,
        observations=5,
        improvement=proposed - current,
        improved=proposed > current,
        regression_detected=False,
        regression_severity="none",
        confidence=80.0,
        rationale="diagnostics test",
    )


def make_approval(strategy="property"):
    return LearningApprovalDecision(
        approved=True,
        strategy=strategy,
        confidence=80.0,
        reason="approved",
    )


def make_checker(tmp_path):
    runtime = RuntimeStateStore(
        tmp_path / "runtime.db"
    )
    learning = PersistentLearningState(runtime)

    return (
        RuntimeDiagnosticsChecker(
            runtime_store=runtime,
            learning_state=learning,
        ),
        runtime,
        learning,
    )


def test_diagnostics_report_initial_runtime_state(tmp_path):
    checker, runtime, learning = make_checker(tmp_path)

    result = checker.check()

    assert isinstance(result, RuntimeDiagnostics)
    assert result.runtime_status is None
    assert result.clean_shutdown is None
    assert result.last_exit_code is None
    assert result.runtime_schema_version == 1
    assert result.active_strategy_count == 0
    assert result.active_strategies == ()
    assert result.rollback_available == ()
    assert result.runtime_state_available is True
    assert result.learning_state_available is True
    assert result.healthy is True
    assert result.issues == ()


def test_diagnostics_report_runtime_lifecycle_state(tmp_path):
    checker, runtime, learning = make_checker(tmp_path)

    runtime.set(
        "runtime.status",
        "ready",
    )
    runtime.set(
        "runtime.clean_shutdown",
        "true",
    )
    runtime.set(
        "runtime.last_exit_code",
        "0",
    )

    result = checker.check()

    assert result.runtime_status == "ready"
    assert result.clean_shutdown is True
    assert result.last_exit_code == 0
    assert result.healthy is True


def test_diagnostics_report_active_governed_strategies(
    tmp_path,
):
    checker, runtime, learning = make_checker(tmp_path)

    application = LearningChangeApplication(
        persistent_state=learning,
    )

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    application.apply(
        proposal=make_proposal(
            strategy="mutation",
            current=70.0,
            proposed=95.0,
        ),
        approval=make_approval(
            strategy="mutation",
        ),
    )

    result = checker.check()

    assert result.active_strategy_count == 2
    assert result.active_strategies == (
        "mutation",
        "property",
    )


def test_diagnostics_report_rollback_availability(
    tmp_path,
):
    checker, runtime, learning = make_checker(tmp_path)

    application = LearningChangeApplication(
        persistent_state=learning,
    )

    application.apply(
        proposal=make_proposal(
            current=70.0,
            proposed=80.0,
        ),
        approval=make_approval(),
    )

    application.apply(
        proposal=make_proposal(
            current=80.0,
            proposed=90.0,
        ),
        approval=make_approval(),
    )

    result = checker.check()

    assert result.rollback_available == (
        "property",
    )


def test_diagnostics_are_read_only(tmp_path):
    checker, runtime, learning = make_checker(tmp_path)

    runtime.set(
        "runtime.status",
        "ready",
    )

    before = runtime.all()

    result = checker.check()

    after = runtime.all()

    assert result.healthy is True
    assert before == after


def test_diagnostics_do_not_change_learning_state(
    tmp_path,
):
    checker, runtime, learning = make_checker(tmp_path)

    application = LearningChangeApplication(
        persistent_state=learning,
    )

    application.apply(
        proposal=make_proposal(),
        approval=make_approval(),
    )

    before = learning.load()

    result = checker.check()

    after = learning.load()

    assert result.active_strategies == (
        "property",
    )
    assert before == after


def test_invalid_exit_code_is_reported_as_issue(
    tmp_path,
):
    checker, runtime, learning = make_checker(tmp_path)

    runtime.set(
        "runtime.last_exit_code",
        "not-a-number",
    )

    result = checker.check()

    assert result.healthy is False
    assert "invalid persisted runtime exit code" in result.issues


def test_diagnostics_detects_corrupt_learning_state(
    tmp_path,
):
    checker, runtime, learning = make_checker(tmp_path)

    runtime.set(
        learning.KEY,
        '{"version":2,"changes":"invalid","history":{}}',
    )

    result = checker.check()

    assert result.learning_state_available is False
    assert result.healthy is False
    assert any(
        "learning state unavailable" in item
        for item in result.issues
    )


def test_diagnostics_are_deterministic(tmp_path):
    checker, runtime, learning = make_checker(tmp_path)

    runtime.set(
        "runtime.status",
        "ready",
    )
    runtime.set(
        "runtime.clean_shutdown",
        "true",
    )
    runtime.set(
        "runtime.last_exit_code",
        "0",
    )

    first = checker.check()
    second = checker.check()

    assert first == second
