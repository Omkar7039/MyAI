from datetime import datetime, timedelta, timezone

from experience.evaluation import (
    ExperienceEvaluationCase,
    ExperienceEvaluator,
)
from experience.store import Experience


def test_experience_evaluator_reports_perfect_result():
    now = datetime.now(timezone.utc)

    experience = Experience(
        experience_id="eval-1",
        task="parser validation bug",
        category="repair",
        action="Updated parser validation and reran regression tests.",
        outcome="Regression tests passed and verification completed.",
        success=True,
        lesson="Keep parser validation aligned with current tests.",
        created_at=(now - timedelta(days=5)).isoformat(),
    )

    case = ExperienceEvaluationCase(
        name="relevant",
        query="parser validation bug",
        experience=experience,
        expected_applicable=True,
        expected_confidence="high",
        expected_freshness="fresh",
    )

    result = ExperienceEvaluator().evaluate([case])

    assert result.total_cases == 1
    assert result.passed_cases == 1
    assert result.failed_cases == 0
    assert result.accuracy == 1.0
    assert result.details == ("relevant: PASS",)


def test_experience_evaluator_reports_failed_expectation():
    now = datetime.now(timezone.utc)

    experience = Experience(
        experience_id="eval-2",
        task="parser validation bug",
        category="repair",
        action="Updated parser validation and reran regression tests.",
        outcome="Regression tests passed and verification completed.",
        success=True,
        lesson="Keep parser validation aligned with current tests.",
        created_at=(now - timedelta(days=5)).isoformat(),
    )

    case = ExperienceEvaluationCase(
        name="intentional-mismatch",
        query="parser validation bug",
        experience=experience,
        expected_applicable=True,
        expected_confidence="low",
        expected_freshness="fresh",
    )

    result = ExperienceEvaluator().evaluate([case])

    assert result.total_cases == 1
    assert result.passed_cases == 0
    assert result.failed_cases == 1
    assert result.accuracy == 0.0
    assert "intentional-mismatch: FAIL" in result.details[0]


def test_experience_evaluator_handles_empty_suite():
    result = ExperienceEvaluator().evaluate([])

    assert result.total_cases == 0
    assert result.passed_cases == 0
    assert result.failed_cases == 0
    assert result.accuracy == 1.0
    assert result.details == ()
