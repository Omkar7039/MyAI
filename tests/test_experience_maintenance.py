from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from experience.lifecycle import ExperienceLifecycleManager
from experience.maintenance import ExperienceLifecycleMaintenance
from experience.store import Experience, ExperienceStore


def _make_experience(experience_id, success, age_days, now):
    return Experience(
        experience_id=experience_id,
        task="Lifecycle maintenance test",
        category="test",
        action="Evaluate historical experience.",
        outcome="Evaluation completed.",
        success=success,
        lesson="Apply lifecycle policy safely.",
        created_at=(now - timedelta(days=age_days)).isoformat(),
    )


def test_lifecycle_maintenance_dry_run_does_not_modify_store():
    now = datetime.now(timezone.utc)

    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        store.add(_make_experience(
            "old-success", True, 800, now
        ))
        store.add(_make_experience(
            "old-failure", False, 800, now
        ))
        store.add(_make_experience(
            "recent", True, 30, now
        ))

        maintenance = ExperienceLifecycleMaintenance(
            store=store,
            manager=ExperienceLifecycleManager(
                archive_after_days=365,
                delete_after_days=730,
            ),
        )

        report = maintenance.run(
            limit=10,
            apply=False,
            now=now,
        )

        assert report.scanned == 3
        assert report.retained == 1
        assert report.archived == 1
        assert report.deleted == 1
        assert store.get("old-success").lifecycle_state == "active"
        assert store.get("old-failure") is not None


def test_lifecycle_maintenance_applies_cleanup():
    now = datetime.now(timezone.utc)

    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        store.add(_make_experience(
            "old-success", True, 800, now
        ))
        store.add(_make_experience(
            "old-failure", False, 800, now
        ))
        store.add(_make_experience(
            "recent", True, 30, now
        ))

        maintenance = ExperienceLifecycleMaintenance(
            store=store,
            manager=ExperienceLifecycleManager(
                archive_after_days=365,
                delete_after_days=730,
            ),
        )

        report = maintenance.run(
            limit=10,
            apply=True,
            now=now,
        )

        assert report.archived == 1
        assert report.deleted == 1
        assert store.get("old-success").lifecycle_state == "archived"
        assert store.get("old-failure") is None
        assert store.get("recent").lifecycle_state == "active"
