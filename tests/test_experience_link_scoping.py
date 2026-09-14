from pathlib import Path
from tempfile import TemporaryDirectory

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore


def test_project_file_and_symbol_link_scoping():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        store = ExperienceProjectLinkStore(
            root / "experience.db"
        )

        current = ExperienceProjectLink(
            experience_id="current",
            project_root=str(root),
            file_paths=(
                "agents/repair.py",
                "project/project_agent.py",
            ),
            symbols=(
                "RepairAgent",
                "RepairAgent.repair_and_verify",
            ),
            commit_id="current",
        )

        other_project = ExperienceProjectLink(
            experience_id="other-project",
            project_root=str(root / "other"),
            file_paths=("agents/repair.py",),
            symbols=("RepairAgent",),
            commit_id="other",
        )

        other_file = ExperienceProjectLink(
            experience_id="other-file",
            project_root=str(root),
            file_paths=("agents/coding.py",),
            symbols=("CodingAgent",),
            commit_id="other-file",
        )

        store.save(current)
        store.save(other_project)
        store.save(other_file)

        project_ids = {
            item.experience_id
            for item in store.search_project(str(root))
        }

        assert project_ids == {
            "current",
            "other-file",
        }

        file_ids = {
            item.experience_id
            for item in store.search_file("agents/repair.py")
        }

        assert file_ids == {
            "current",
            "other-project",
        }

        symbol_ids = {
            item.experience_id
            for item in store.search_symbol(
                "RepairAgent.repair_and_verify"
            )
        }

        assert symbol_ids == {"current"}
