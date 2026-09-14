from experience.conflict import ExperienceConflictDetector
from experience.retriever import RetrievedExperience
from experience.store import Experience


def test_experience_conflict_detection():
    detector = ExperienceConflictDetector()

    success = RetrievedExperience(
        experience=Experience(
            experience_id="success",
            task="Fix parser validation",
            category="repair",
            action="Updated parser validation and verified regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep parser validation aligned with current tests.",
            metadata="",
        ),
        score=61.0,
    )

    failure = RetrievedExperience(
        experience=Experience(
            experience_id="failure",
            task="Fix parser validation",
            category="repair",
            action="Changed parser validation without sufficient testing.",
            outcome="Regression failed.",
            success=False,
            lesson="Do not repeat this approach without fresh verification.",
            metadata="",
        ),
        score=40.0,
    )

    no_conflict = detector.detect([success], [])

    assert not no_conflict.detected
    assert no_conflict.text == ""

    conflict = detector.detect([success], [failure])

    assert conflict.detected
    assert len(conflict.successful) == 1
    assert len(conflict.warnings) == 1
    assert "CONFLICTING HISTORICAL EXPERIENCE:" in conflict.text
    assert "inconclusive" in conflict.text.lower()
    assert "authoritative" in conflict.text.lower()
