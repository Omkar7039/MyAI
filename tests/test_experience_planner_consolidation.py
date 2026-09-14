from experience.planner import ExperiencePlanner
from experience.retriever import RetrievedExperience
from experience.store import Experience


class FakeRetriever:
    def successful(self, task, limit=3):
        return [RetrievedExperience(
            experience=Experience(
                experience_id="success-consolidation",
                task="Fix parser validation",
                category="repair",
                action="Updated validation and added regression coverage.",
                outcome="Regression tests passed.",
                success=True,
                lesson="Keep validation aligned with current tests.",
            ),
            score=70.0,
        )]

    def warnings(self, task, limit=3):
        return [RetrievedExperience(
            experience=Experience(
                experience_id="failure-consolidation",
                task="Fix parser validation",
                category="repair",
                action="Replaced validation logic broadly.",
                outcome="Regression tests failed.",
                success=False,
                lesson="Avoid broad changes without fresh verification.",
            ),
            score=40.0,
        )]


def test_planner_surfaces_consolidated_experience():
    planner = ExperiencePlanner(
        retriever=FakeRetriever(),
        max_chars=1600,
    )

    guidance = planner.plan("Fix parser validation")

    assert guidance.consolidation is not None
    assert guidance.consolidation.task == "Fix parser validation"
    assert len(guidance.consolidation.experience_ids) == 2
    assert "CONSOLIDATED HISTORICAL EXPERIENCE:" in guidance.text
    assert "Successful approaches:" in guidance.text
    assert "Warnings from failed attempts:" in guidance.text
    assert "HISTORICAL CONTRADICTION ANALYSIS:" in guidance.text
    assert "fresh verification" in guidance.text.lower()
    assert len(guidance.text) <= 1600
