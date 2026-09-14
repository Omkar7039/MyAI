from pathlib import Path
from tempfile import TemporaryDirectory

from experience.store import Experience, ExperienceStore


def test_experience_store_archive_and_delete():
    with TemporaryDirectory() as tmp:
        store = ExperienceStore(Path(tmp) / "experience.db")

        experience = Experience(
            experience_id="lifecycle-test",
            task="Lifecycle test",
            category="test",
            action="Archive an old experience.",
            outcome="Archive completed.",
            success=True,
            lesson="Archived experiences remain available by ID.",
        )

        store.add(experience)

        active = store.get("lifecycle-test")
        assert active is not None
        assert active.lifecycle_state == "active"

        assert store.archive("lifecycle-test")

        archived = store.get("lifecycle-test")
        assert archived is not None
        assert archived.lifecycle_state == "archived"
        assert store.search("Lifecycle test") == []
        assert store.recent() == []

        assert store.delete("lifecycle-test")
        assert store.get("lifecycle-test") is None
