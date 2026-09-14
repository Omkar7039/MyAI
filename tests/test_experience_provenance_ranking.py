from pathlib import Path
from tempfile import TemporaryDirectory

from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_provenance_aware_experience_ranking():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        common = dict(
            task="Fix parser validation bug",
            category="repair",
            action="Updated parser validation and reran regression tests.",
            outcome="Regression tests passed.",
            success=True,
            created_at="2026-09-01 00:00:00",
        )

        store.add(
            Experience(
                experience_id="proven",
                metadata='{"provenance":{"source":"repair","workflow":"repair_and_verify","evidence":["regression tests passed","mutation verification passed","property verification passed"],"verified":true}}',
                lesson="A verified parser repair should be checked against current tests.",
                **common,
            )
        )

        store.add(
            Experience(
                experience_id="plain",
                metadata="",
                lesson="A parser repair was recorded as successful.",
                **common,
            )
        )

        results = ExperienceRetriever(store).search(
            "parser validation bug",
            limit=2,
            include_failures=False,
        )

        by_id = {
            item.experience.experience_id: item
            for item in results
        }

        assert len(results) == 2
        assert by_id["proven"].score > by_id["plain"].score
        assert results[0].experience.experience_id == "proven"
