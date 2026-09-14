from pathlib import Path
from tempfile import TemporaryDirectory

from experience.planner import ExperiencePlanner
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_planner_exposes_experience_confidence():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        store.add(
            Experience(
                experience_id="parser",
                task="Fix parser validation bug",
                category="repair",
                action="Updated parser validation and reran regression tests.",
                outcome="Regression tests passed.",
                success=True,
                lesson="Verify parser changes against current tests.",
            )
        )

        planner = ExperiencePlanner(
            retriever=ExperienceRetriever(store),
            max_chars=1600,
        )

        guidance = planner.plan("parser validation bug")

        assert guidance.confidences
        assert guidance.confidences[0][0] == "parser"

        confidence = guidance.confidences[0][1]

        assert confidence.label in ("high", "medium", "low")
        assert 0.0 <= confidence.score <= 100.0
        assert "Confidence:" in guidance.text
