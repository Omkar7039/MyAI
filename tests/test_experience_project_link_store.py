from pathlib import Path
from tempfile import TemporaryDirectory

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore


def _link(experience_id, project_root, files, symbols=(), commit_id=""):
    return ExperienceProjectLink(
        experience_id=experience_id,
        project_root=project_root,
        file_paths=tuple(files),
        symbols=tuple(symbols),
        commit_id=commit_id,
    )


def test_project_link_store_round_trip_and_project_search():
    with TemporaryDirectory() as tmp:
        store = ExperienceProjectLinkStore(
            Path(tmp) / "experience.db"
        )

        link = _link(
            "exp-1",
            "/projects/MyAI",
            ("agents/repair.py", "project/project_agent.py"),
            ("RepairAgent", "ProjectAgent"),
            "abc123",
        )

        store.save(link)

        assert store.get("exp-1") == link
        assert store.search_project("/projects/MyAI") == [link]


def test_project_link_store_searches_exact_file_membership():
    with TemporaryDirectory() as tmp:
        store = ExperienceProjectLinkStore(
            Path(tmp) / "experience.db"
        )

        first = _link(
            "exp-1",
            "/projects/MyAI",
            ("agents/repair.py", "project/project_agent.py"),
        )
        second = _link(
            "exp-2",
            "/projects/MyAI",
            ("agents/coding.py",),
        )

        store.save(first)
        store.save(second)

        assert store.search_file("agents/repair.py") == [first]
        assert store.search_file("agents/coding.py") == [second]
        assert store.search_file("agents/missing.py") == []


def test_project_link_store_delete_is_idempotent():
    with TemporaryDirectory() as tmp:
        store = ExperienceProjectLinkStore(
            Path(tmp) / "experience.db"
        )

        link = _link(
            "exp-1",
            "/projects/MyAI",
            ("agents/repair.py",),
        )

        store.save(link)

        assert store.delete("exp-1")
        assert not store.delete("exp-1")
        assert store.get("exp-1") is None
