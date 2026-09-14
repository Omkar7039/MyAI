from pathlib import Path
from tempfile import TemporaryDirectory

from experience.planner import ExperiencePlanner
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_planner_surfaces_conflicting_history():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        store.add(
            Experience(
                experience_id="success",
                task="Fix parser validation bug",
                category="repair",
                action="Updated parser validation and verified regression tests.",
                outcome="Regression tests passed.",
                success=True,
                lesson="Keep parser validation aligned with current tests.",
                metadata="",
            )
        )

        store.add(
            Experience(
                experience_id="failure",
                task="Fix parser validation bug",
                category="repair",
                action="Changed parser validation without sufficient testing.",
                outcome="Regression failed.",
                success=False,
                lesson="Do not repeat this approach without fresh verification.",
                metadata="",
            )
        )

        planner = ExperiencePlanner(
            retriever=ExperienceRetriever(store),
            max_chars=1600,
        )

        guidance = planner.plan("parser validation bug")

        assert len(guidance.successful) == 1
        assert len(guidance.warnings) == 1
        assert "CONFLICTING HISTORICAL EXPERIENCE:" in guidance.text
        assert "inconclusive" in guidance.text.lower()
        assert "authoritative" in guidance.text.lower()
