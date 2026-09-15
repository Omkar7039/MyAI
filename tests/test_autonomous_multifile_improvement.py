from agents.autonomous_multifile_improvement import (
    MultiFileRepairImprovementPlanner,
)


def test_planning_failure_produces_new_strategy():
    improvement = MultiFileRepairImprovementPlanner().plan(
        {
            "stage": "planning",
            "errors": ["planner failed"],
            "rolled_back": False,
        }
    )

    assert "new minimal patch plan" in improvement.strategy
    assert improvement.constraints
    assert "planning" in improvement.reason.lower()


def test_validation_failure_requires_safer_patch():
    improvement = MultiFileRepairImprovementPlanner().plan(
        {
            "stage": "validation",
            "errors": ["unsafe patch"],
            "rolled_back": False,
        }
    )

    assert "Reduce the patch" in improvement.strategy
    assert "invalid patch" in improvement.constraints[0]


def test_rollback_failure_changes_repair_strategy():
    improvement = MultiFileRepairImprovementPlanner().plan(
        {
            "stage": "post_apply_verification",
            "errors": ["verification failed"],
            "rolled_back": True,
        }
    )

    assert "Change the repair approach" in improvement.strategy
    assert "rolled back" in improvement.constraints[0]


def test_unknown_failure_requests_more_evidence():
    improvement = MultiFileRepairImprovementPlanner().plan(
        {
            "stage": "unknown",
            "errors": [],
            "rolled_back": False,
        }
    )

    assert "stronger evidence" in improvement.strategy.lower()
    assert "unsupported repair" in improvement.constraints[0]


def test_directive_contains_strategy_reason_and_constraints():
    planner = MultiFileRepairImprovementPlanner()

    improvement = planner.plan(
        {
            "stage": "validation",
            "errors": ["invalid patch"],
            "rolled_back": False,
        }
    )

    directive = planner.build_directive(improvement)

    assert "AUTONOMOUS REPAIR IMPROVEMENT:" in directive
    assert improvement.strategy in directive
    assert improvement.reason in directive
    assert "Constraints:" in directive


def test_improvement_planning_is_deterministic():
    attempt = {
        "stage": "post_apply_verification",
        "errors": ["verification failed"],
        "rolled_back": True,
    }

    planner = MultiFileRepairImprovementPlanner()

    assert planner.plan(attempt) == planner.plan(attempt)
