from core.runtime_consistency import RuntimeConsistencyReport
from core.runtime_diagnostics import RuntimeDiagnostics
from core.runtime_mode import RuntimeMode, RuntimeModeEvaluator


def diagnostics(
    *,
    runtime_state_available=True,
    learning_state_available=True,
    healthy=True,
):
    return RuntimeDiagnostics(
        runtime_status="ready",
        clean_shutdown=False,
        last_exit_code=None,
        runtime_schema_version=1,
        active_strategy_count=0,
        active_strategies=(),
        rollback_available=(),
        runtime_state_available=runtime_state_available,
        learning_state_available=learning_state_available,
        healthy=healthy,
        issues=(),
    )


def consistency(
    *,
    consistent=True,
    issues=(),
):
    return RuntimeConsistencyReport(
        consistent=consistent,
        issues=issues,
    )


def test_healthy_runtime_is_normal():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(),
        consistency(),
    )

    assert isinstance(result, RuntimeMode)
    assert result.mode == "normal"
    assert result.accept_tasks is True
    assert result.learning_enabled is True


def test_learning_state_unavailable_enters_degraded_mode():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(
            learning_state_available=False,
            healthy=False,
        ),
        consistency(),
    )

    assert result.mode == "degraded"
    assert result.accept_tasks is True
    assert result.learning_enabled is False
    assert "learning state" in result.reason


def test_other_diagnostic_problem_enters_degraded_mode():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(
            healthy=False,
        ),
        consistency(),
    )

    assert result.mode == "degraded"
    assert result.accept_tasks is True
    assert result.learning_enabled is False


def test_consistency_failure_requires_recovery():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(),
        consistency(
            consistent=False,
            issues=("invalid runtime status",),
        ),
    )

    assert result.mode == "recovery"
    assert result.accept_tasks is False
    assert result.learning_enabled is False
    assert "invalid runtime status" in result.reason


def test_runtime_state_unavailable_stops_operation():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(
            runtime_state_available=False,
            healthy=False,
        ),
        consistency(),
    )

    assert result.mode == "stopped"
    assert result.accept_tasks is False
    assert result.learning_enabled is False


def test_consistency_failure_takes_priority_over_degraded_diagnostics():
    result = RuntimeModeEvaluator().evaluate(
        diagnostics(
            learning_state_available=False,
            healthy=False,
        ),
        consistency(
            consistent=False,
            issues=("runtime metadata inconsistent",),
        ),
    )

    assert result.mode == "recovery"


def test_mode_evaluation_is_deterministic():
    evaluator = RuntimeModeEvaluator()

    first = evaluator.evaluate(
        diagnostics(),
        consistency(),
    )
    second = evaluator.evaluate(
        diagnostics(),
        consistency(),
    )

    assert first == second
