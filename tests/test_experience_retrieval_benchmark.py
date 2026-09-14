from pathlib import Path
from tempfile import TemporaryDirectory

from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore


def test_experience_retrieval_benchmark_ranks_verified_fresh_history_first():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / 'experience.db')

        store.add(
            Experience(
                experience_id='verified-fresh',
                task='Fix parser validation bug',
                category='repair',
                action='Updated parser validation and reran the regression test suite.',
                outcome='Regression tests passed and mutation verification passed.',
                success=True,
                lesson='A verified parser repair should always be checked against current tests.',
                metadata='{"provenance":{"source":"repair","workflow":"repair_and_verify","evidence":["regression tests passed","mutation verification passed"],"verified":true}}',
                created_at='2026-09-10 00:00:00',
            )
        )

        store.add(
            Experience(
                experience_id='verified-old',
                task='Fix parser validation bug',
                category='repair',
                action='Updated parser validation and reran regression tests.',
                outcome='Regression tests passed and mutation verification passed.',
                success=True,
                lesson='A verified parser repair from older project history should still be checked against current tests.',
                metadata='{"provenance":{"source":"repair","workflow":"repair_and_verify","evidence":["regression tests passed"],"verified":true}}',
                created_at='2025-01-01 00:00:00',
            )
        )

        store.add(
            Experience(
                experience_id='weak',
                task='Fix parser validation bug',
                category='repair',
                action='Changed the parser.',
                outcome='It worked.',
                success=True,
                lesson='Remember this fix.',
                created_at='2026-09-10 00:00:00',
            )
        )

        store.add(
            Experience(
                experience_id='failed',
                task='Fix parser validation bug',
                category='repair',
                action='Changed parser logic without sufficient testing.',
                outcome='Regression failed.',
                success=False,
                lesson='Do not reuse this approach without fresh verification.',
                created_at='2026-09-10 00:00:00',
            )
        )

        results = ExperienceRetriever(store).search(
            'parser validation bug',
            limit=4,
            include_failures=True,
        )

        by_id = {
            item.experience.experience_id: item
            for item in results
        }

        assert len(results) == 4
        assert results[0].experience.experience_id == 'verified-fresh'
        assert by_id['verified-fresh'].score > by_id['verified-old'].score
        assert by_id['verified-fresh'].score > by_id['weak'].score
        assert by_id['verified-fresh'].score > by_id['failed'].score


def test_experience_retrieval_benchmark_can_exclude_failures():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / 'experience.db')

        store.add(
            Experience(
                experience_id='success',
                task='Fix parser validation bug',
                category='repair',
                action='Updated parser validation.',
                outcome='Regression tests passed.',
                success=True,
                lesson='Verify parser changes against current tests.',
            )
        )

        store.add(
            Experience(
                experience_id='failure',
                task='Fix parser validation bug',
                category='repair',
                action='Changed parser incorrectly.',
                outcome='Regression tests failed.',
                success=False,
                lesson='Avoid repeating the failed approach.',
            )
        )

        results = ExperienceRetriever(store).search(
            'parser validation bug',
            limit=10,
            include_failures=False,
        )

        assert results
        assert all(item.experience.success for item in results)
