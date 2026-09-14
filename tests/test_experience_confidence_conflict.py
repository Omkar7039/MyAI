from experience.applicability import ExperienceApplicabilityFilter
from experience.confidence import ExperienceConfidenceCalculator
from experience.conflict import ExperienceConflictDetector
from experience.freshness import ExperienceFreshnessCalculator
from experience.retriever import RetrievedExperience
from experience.store import Experience


def _result(experience_id, success, score):
    return RetrievedExperience(
        experience=Experience(
            experience_id=experience_id,
            task="Fix parser validation bug",
            category="repair",
            action=(
                "Updated parser validation and verified regression tests."
                if success
                else "Changed parser validation without sufficient testing."
            ),
            outcome=(
                "Regression tests passed."
                if success
                else "Regression tests failed."
            ),
            success=success,
            lesson=(
                "Keep parser validation aligned with current tests."
                if success
                else "Require fresh verification before repeating the approach."
            ),
            created_at="2026-09-10 00:00:00",
        ),
        score=score,
    )


def test_conflicting_history_reduces_experience_confidence():
    successful = _result("success", True, 70.0)
    failed = _result("failure", False, 40.0)

    applicability = ExperienceApplicabilityFilter()
    freshness = ExperienceFreshnessCalculator()
    confidence = ExperienceConfidenceCalculator()
    detector = ExperienceConflictDetector()

    successful_app = applicability.evaluate(
        "parser validation bug",
        successful,
    )

    successful_freshness = freshness.calculate(
        successful.experience,
    )

    baseline = confidence.calculate(
        successful,
        successful_app,
        successful_freshness,
    )

    conflict = detector.detect(
        [successful],
        [failed],
    )

    conflicted = confidence.calculate(
        successful,
        successful_app,
        successful_freshness,
        conflict=conflict,
    )

    assert conflict.detected
    assert conflicted.score < baseline.score
    assert conflicted.score == baseline.score - 25.0
    assert conflicted.label == "medium"
    assert any(
        "conflicting historical outcomes" in reason.lower()
        for reason in conflicted.reasons
    )
