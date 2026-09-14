from pathlib import Path
from tempfile import TemporaryDirectory

from experience.planner import ExperiencePlanner
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_planner_filters_irrelevant_experiences():
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
                metadata="",
            )
        )

        store.add(
            Experience(
                experience_id="database",
                task="Fix database connection timeout",
                category="repair",
                action="Updated connection retry handling.",
                outcome="Connection tests passed.",
                success=True,
                lesson="Retry transient database failures.",
                metadata="",
            )
        )

        planner = ExperiencePlanner(
            retriever=ExperienceRetriever(store),
            max_chars=1600,
        )

        guidance = planner.plan("parser validation bug")

        assert len(guidance.successful) == 1
        assert guidance.successful[0].experience.experience_id == "parser"
        assert "Fix parser validation bug" in guidance.text
        assert "Fix database connection timeout" not in guidance.text
