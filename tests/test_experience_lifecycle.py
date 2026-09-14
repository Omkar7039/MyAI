from datetime import datetime, timedelta, timezone

from experience.lifecycle import ExperienceLifecycleManager
from experience.store import Experience


NOW = datetime.now(timezone.utc)


def _experience(experience_id, success, age_days, created=True):
    created_at = ""
    if created:
        created_at = (NOW - timedelta(days=age_days)).isoformat()

    return Experience(
        experience_id=experience_id,
        task="Fix parser validation",
        category="repair",
        action="Updated validation logic.",
        outcome="Verification completed.",
        success=success,
        lesson="Keep validation aligned with current tests.",
        created_at=created_at,
    )


def test_lifecycle_retains_recent_experience():
    manager = ExperienceLifecycleManager()

    result = manager.classify(
        _experience("recent", True, 30),
        now=NOW,
    )

    assert result.action == "retain"


def test_lifecycle_archives_old_successful_experience():
    manager = ExperienceLifecycleManager(
        archive_after_days=365,
        delete_after_days=730,
    )

    result = manager.classify(
        _experience("old-success", True, 800),
        now=NOW,
    )

    assert result.action == "archive"


def test_lifecycle_deletes_old_failed_experience():
    manager = ExperienceLifecycleManager(
        archive_after_days=365,
        delete_after_days=730,
    )

    result = manager.classify(
        _experience("old-failure", False, 800),
        now=NOW,
    )

    assert result.action == "delete"


def test_lifecycle_retains_unknown_age_conservatively():
    manager = ExperienceLifecycleManager()

    result = manager.classify(
        _experience("unknown-age", False, 0, created=False),
        now=NOW,
    )

    assert result.action == "retain"
    assert "Missing age metadata" in result.reason
