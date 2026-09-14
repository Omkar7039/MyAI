from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from experience.lifecycle import ExperienceLifecycleManager
from experience.maintenance import ExperienceLifecycleMaintenance
from experience.planner import ExperiencePlanner
from experience.recorder import ExperienceRecorder
from experience.retriever import ExperienceRetriever
from experience.store import ExperienceStore


def test_experience_memory_end_to_end_workflow():
    with TemporaryDirectory() as tmp:
        db = Path(tmp) / 'experience.db'

        store = ExperienceStore(db)
        recorder = ExperienceRecorder(store=store)
        retriever = ExperienceRetriever(store)
        planner = ExperiencePlanner(
            retriever=retriever,
            max_chars=1600,
        )

        experience = recorder.record_repair(
            task='Fix parser validation bug',
            action='Updated parser validation and reran regression tests.',
            outcome='Regression behavior verified successfully.',
            success=True,
            lesson='Verify parser changes against the current regression tests.',
        )

        assert experience.experience_id
        assert store.get(experience.experience_id) is not None

        retrieved = retriever.search('parser validation bug', limit=5)
        assert retrieved
        assert retrieved[0].experience.experience_id == experience.experience_id

        guidance = planner.plan('parser validation bug')

        assert guidance.successful
        assert guidance.successful[0].experience.experience_id == experience.experience_id
        assert 'Fix parser validation bug' in guidance.text
        assert 'current regression tests' in guidance.text

        maintenance = ExperienceLifecycleMaintenance(
            store=store,
            manager=ExperienceLifecycleManager(),
        )

        report = maintenance.run(
            limit=1000,
            apply=False,
            now=datetime.now(timezone.utc),
        )

        assert report.scanned == 1
        assert report.retained == 1
        assert report.archived == 0
        assert report.deleted == 0

        assert store.get(experience.experience_id) is not None
        assert planner.plan('parser validation bug').successful[0].experience.experience_id == experience.experience_id
