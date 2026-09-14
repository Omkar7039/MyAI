from experience.applicability import ExperienceApplicability
from experience.confidence import ExperienceConfidenceCalculator
from experience.conflict import ExperienceConflict
from experience.freshness import ExperienceFreshness
from experience.retriever import RetrievedExperience
from experience.store import Experience


def test_experience_confidence_scoring():
    calculator = ExperienceConfidenceCalculator()

    strong = RetrievedExperience(
        experience=Experience(
            experience_id="strong",
            task="Fix parser validation bug",
            category="repair",
            action="Updated parser validation and verified regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep parser validation aligned with current tests.",
            metadata="",
        ),
        score=70.0,
    )

    applicable = ExperienceApplicability(
        applicable=True,
        score=100.0,
        reason="Applicable",
    )

    fresh = ExperienceFreshness(
        age_days=10.0,
        score=0.96,
        label="fresh",
    )

    high = calculator.calculate(
        strong,
        applicable,
        fresh,
    )

    conflict = ExperienceConflict(
        detected=True,
        successful=[strong],
        warnings=[],
        text="conflict",
    )

    conflicted = calculator.calculate(
        strong,
        applicable,
        fresh,
        conflict=conflict,
    )

    failed = RetrievedExperience(
        experience=Experience(
            experience_id="failed",
            task="Fix parser validation bug",
            category="repair",
            action="Changed parser without sufficient testing.",
            outcome="Regression failed.",
            success=False,
            lesson="Require fresh verification.",
            metadata="",
        ),
        score=40.0,
    )

    low = calculator.calculate(
        failed,
        ExperienceApplicability(
            applicable=False,
            score=10.0,
            reason="Weak applicability",
        ),
        ExperienceFreshness(
            age_days=700.0,
            score=0.07,
            label="old",
        ),
    )

    assert high.score > conflicted.score
    assert high.score > low.score
    assert high.label == "high"
    assert conflicted.label == "medium"
    assert low.label == "low"
    assert any(
        "Conflicting" in reason
        for reason in conflicted.reasons
    )
