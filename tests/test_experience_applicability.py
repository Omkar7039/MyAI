from experience.applicability import ExperienceApplicabilityFilter
from experience.retriever import RetrievedExperience
from experience.store import Experience


def test_experience_applicability_filter():
    engine = ExperienceApplicabilityFilter()

    relevant = RetrievedExperience(
        experience=Experience(
            experience_id="relevant",
            task="Fix parser validation bug",
            category="repair",
            action="Updated parser validation and reran regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Verify parser changes against current tests.",
            metadata="",
        ),
        score=61.0,
    )

    irrelevant = RetrievedExperience(
        experience=Experience(
            experience_id="irrelevant",
            task="Fix database connection timeout",
            category="repair",
            action="Updated connection retry handling.",
            outcome="Connection tests passed.",
            success=True,
            lesson="Retry transient database failures.",
            metadata="",
        ),
        score=18.0,
    )

    good = engine.evaluate(
        "parser validation bug",
        relevant,
    )

    bad = engine.evaluate(
        "parser validation bug",
        irrelevant,
    )

    assert good.applicable
    assert good.score > bad.score
    assert not bad.applicable
