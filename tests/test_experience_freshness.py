from pathlib import Path
from datetime import datetime, timezone

from experience.freshness import ExperienceFreshnessCalculator
from experience.retriever import RetrievedExperience
from experience.store import Experience, ExperienceStore


def test_experience_freshness_decay():
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)

    recent = RetrievedExperience(
        experience=Experience(
            experience_id="recent",
            task="recent repair",
            category="repair",
            action="verified repair",
            outcome="tests passed",
            success=True,
            lesson="use current tests",
            created_at="2026-09-01 00:00:00",
        ),
        score=50.0,
    )

    old = RetrievedExperience(
        experience=Experience(
            experience_id="old",
            task="old repair",
            category="repair",
            action="verified repair",
            outcome="tests passed",
            success=True,
            lesson="use current tests",
            created_at="2025-01-01 00:00:00",
        ),
        score=50.0,
    )

    calculator = ExperienceFreshnessCalculator()

    recent_result = calculator.calculate(recent, now=now)
    old_result = calculator.calculate(old, now=now)

    assert recent_result.score > old_result.score
    assert recent_result.age_days < old_result.age_days
    assert recent_result.label == "fresh"
    assert old_result.label == "old"


def test_experience_created_at_round_trip(tmp_path):
    store = ExperienceStore(Path(tmp_path) / "experience.db")

    original = Experience(
        experience_id="roundtrip",
        task="test persistence",
        category="repair",
        action="store an experience",
        outcome="experience retrieved successfully",
        success=True,
        lesson="created_at must survive persistence",
        metadata="test=true",
    )

    store.add(original)

    loaded = store.get("roundtrip")

    assert loaded is not None
    assert loaded.created_at
    datetime.fromisoformat(
        loaded.created_at.replace("Z", "+00:00")
    )
