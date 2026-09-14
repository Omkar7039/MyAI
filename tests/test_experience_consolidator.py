from experience.consolidator import ExperienceConsolidator
from experience.retriever import RetrievedExperience
from experience.store import Experience


def _experience(experience_id, success, action, outcome, lesson):
    return RetrievedExperience(
        experience=Experience(
            experience_id=experience_id,
            task="Fix parser validation",
            category="repair",
            action=action,
            outcome=outcome,
            success=success,
            lesson=lesson,
        ),
        score=60.0,
    )


def test_experience_consolidator_combines_history():
    success = _experience(
        "success-1",
        True,
        "Updated validation and added regression coverage.",
        "Regression tests passed.",
        "Keep validation aligned with the current tests.",
    )

    failure = _experience(
        "failure-1",
        False,
        "Replaced validation logic broadly.",
        "Regression tests failed.",
        "Avoid broad validation changes without fresh verification.",
    )

    result = ExperienceConsolidator().consolidate(
        [success, failure],
        max_chars=1200,
    )

    assert result.task == "Fix parser validation"
    assert result.experience_ids == ("success-1", "failure-1")
    assert "Successful approaches:" in result.summary
    assert "Warnings from failed attempts:" in result.summary
    assert "fresh verification" in result.summary
    assert "authoritative" in result.summary
    assert len(result.summary) <= 1200


def test_experience_consolidator_handles_empty_history():
    result = ExperienceConsolidator().consolidate([])

    assert result.task == ""
    assert result.experience_ids == ()
    assert "No experiences available" in result.summary
