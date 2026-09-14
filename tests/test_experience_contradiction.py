from experience.contradiction import ExperienceContradictionResolver
from experience.retriever import RetrievedExperience
from experience.store import Experience


def test_experience_contradiction_resolution():
    resolver = ExperienceContradictionResolver()

    success = RetrievedExperience(
        experience=Experience(
            experience_id="success",
            task="Fix parser validation",
            category="repair",
            action="Updated parser validation.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep parser validation aligned with tests.",
        ),
        score=70.0,
    )

    failure = RetrievedExperience(
        experience=Experience(
            experience_id="failure",
            task="Fix parser validation",
            category="repair",
            action="Replaced parser validation logic.",
            outcome="Regression tests failed.",
            success=False,
            lesson="Do not change parser validation without fresh verification.",
        ),
        score=40.0,
    )

    none = resolver.resolve([success], [])

    assert not none.detected
    assert none.dimensions == ()

    conflict = resolver.resolve(
        [success],
        [failure],
    )

    assert conflict.detected
    assert "action" in conflict.dimensions
    assert "outcome" in conflict.dimensions
    assert "lesson" in conflict.dimensions
    assert "fresh verification" in conflict.recommendation.lower()
