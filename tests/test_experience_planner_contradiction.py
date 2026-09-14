from experience.planner import ExperiencePlanner
from experience.retriever import RetrievedExperience
from experience.store import Experience


class FakeRetriever:
    def successful(self, task, limit=3):
        return [self._success()]

    def warnings(self, task, limit=3):
        return [self._failure()]

    def _success(self):
        return RetrievedExperience(
            experience=Experience(
                experience_id="planner-success",
                task="Fix parser validation",
                category="repair",
                action="Updated parser validation.",
                outcome="Regression tests passed.",
                success=True,
                lesson="Keep parser validation aligned with tests.",
            ),
            score=70.0,
        )

    def _failure(self):
        return RetrievedExperience(
            experience=Experience(
                experience_id="planner-failure",
                task="Fix parser validation",
                category="repair",
                action="Replaced parser validation logic.",
                outcome="Regression tests failed.",
                success=False,
                lesson="Do not change parser validation without fresh verification.",
            ),
            score=40.0,
        )


def test_planner_surfaces_historical_contradiction():
    planner = ExperiencePlanner(
        retriever=FakeRetriever(),
        max_chars=1600,
    )

    guidance = planner.plan("Fix parser validation")

    assert guidance.contradiction is not None
    assert guidance.contradiction.detected
    assert "action" in guidance.contradiction.dimensions
    assert "outcome" in guidance.contradiction.dimensions
    assert "lesson" in guidance.contradiction.dimensions
    assert "HISTORICAL CONTRADICTION ANALYSIS:" in guidance.text
    assert "fresh verification" in guidance.text.lower()
    assert len(guidance.text) <= 1600
