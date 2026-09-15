from agents.autonomous_multifile_retry import (
    AutonomousMultiFileRetryPlanner,
    RetryContext,
)


def test_retry_context_renders_previous_failure():
    context = RetryContext(
        attempt=1,
        previous_stage="post_apply_verification",
        previous_errors=("verification failed",),
        previous_rolled_back=True,
    )

    rendered = context.render()

    assert "Previous attempt: 1" in rendered
    assert "Previous stage: post_apply_verification" in rendered
    assert "Previous rollback: True" in rendered
    assert "verification failed" in rendered


def test_first_attempt_keeps_original_request():
    planner = AutonomousMultiFileRetryPlanner()

    request = planner.build_request(
        "Fix the parser",
        None,
    )

    assert request == "Fix the parser"


def test_retry_request_contains_failure_context():
    planner = AutonomousMultiFileRetryPlanner()

    context = RetryContext(
        attempt=1,
        previous_stage="post_apply_verification",
        previous_errors=(
            "test_a failed",
            "test_b failed",
        ),
        previous_rolled_back=True,
    )

    request = planner.build_request(
        "Fix the parser",
        context,
    )

    assert "Fix the parser" in request
    assert "AUTONOMOUS RETRY CONTEXT:" in request
    assert "test_a failed" in request
    assert "test_b failed" in request
    assert "Do not blindly repeat" in request


def test_retry_planning_is_deterministic():
    planner = AutonomousMultiFileRetryPlanner()

    context = RetryContext(
        attempt=1,
        previous_stage="validation",
        previous_errors=("failed",),
        previous_rolled_back=True,
    )

    first = planner.build_request("Repair project", context)
    second = planner.build_request("Repair project", context)

    assert first == second
