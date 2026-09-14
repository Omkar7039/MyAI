from experience.applicability import ExperienceApplicability
from experience.confidence import ExperienceConfidenceCalculator
from experience.freshness import ExperienceFreshness
from experience.retriever import RetrievedExperience
from experience.store import Experience


def test_non_applicable_experience_has_low_confidence():
    experience = Experience(
        experience_id="irrelevant",
        task="Fix parser validation bug",
        category="repair",
        action="Updated parser validation and reran tests.",
        outcome="Regression tests passed.",
        success=True,
        lesson="Keep parser validation aligned with current tests.",
    )

    result = RetrievedExperience(
        experience=experience,
        score=70.0,
    )

    applicability = ExperienceApplicability(
        applicable=False,
        score=0.0,
        reason="No meaningful task overlap.",
    )

    freshness = ExperienceFreshness(
        age_days=5.0,
        score=0.98,
        label="fresh",
    )

    confidence = ExperienceConfidenceCalculator().calculate(
        result,
        applicability,
        freshness,
    )

    assert confidence.label == "low"
    assert confidence.score < 55.0
    assert any(
        "not applicable" in reason.lower()
        for reason in confidence.reasons
    )
