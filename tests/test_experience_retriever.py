from pathlib import Path
from tempfile import TemporaryDirectory

from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_quality_aware_experience_ranking():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        store.add(
            Experience(
                experience_id="strong",
                task="Fix the parser validation bug",
                category="repair",
                action="Updated parser validation and reran the regression test suite.",
                outcome="Regression tests passed and mutation verification passed.",
                success=True,
                lesson=(
                    "A verified parser repair should always be checked "
                    "against current tests."
                ),
                metadata="attempts=1",
            )
        )

        store.add(
            Experience(
                experience_id="weak",
                task="Fix the parser validation bug",
                category="repair",
                action="Changed the parser.",
                outcome="It worked.",
                success=True,
                lesson="Remember this fix.",
                metadata="",
            )
        )

        store.add(
            Experience(
                experience_id="failed",
                task="Fix the parser validation bug",
                category="repair",
                action="Changed parser logic without sufficient testing.",
                outcome="Regression failed.",
                success=False,
                lesson="Do not reuse this approach without fresh verification.",
                metadata="",
            )
        )

        retriever = ExperienceRetriever(store)

        results = retriever.search(
            "parser validation bug",
            limit=3,
            include_failures=True,
        )

        by_id = {
            item.experience.experience_id: item
            for item in results
        }

        assert len(results) == 3
        assert by_id["strong"].score > by_id["weak"].score
        assert by_id["strong"].score > by_id["failed"].score
        assert results[0].experience.experience_id == "strong"
        assert not by_id["failed"].experience.success
