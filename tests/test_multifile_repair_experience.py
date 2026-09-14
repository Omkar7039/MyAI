from pathlib import Path
from tempfile import TemporaryDirectory

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore
from agents.multi_file_repair import MultiFileRepairPlanner


class Target:
    file = "agents/repair.py"
    symbol = "RepairAgent.repair_and_verify"


class Plan:
    targets = [Target()]
    affected_files = ["agents/repair.py"]
    dependencies = []
    flow = []


def _planner(root):
    planner = MultiFileRepairPlanner.__new__(
        MultiFileRepairPlanner
    )
    planner.root = root
    planner.experience_link_store = ExperienceProjectLinkStore(
        root / "experience.db"
    )
    planner.experience_store = ExperienceStore(
        root / "experience.db"
    )
    planner.experience_retriever = ExperienceRetriever(
        planner.experience_store
    )
    return planner


def test_multifile_repair_prompt_includes_current_project_experience():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        store = ExperienceStore(root / "experience.db")
        links = ExperienceProjectLinkStore(root / "experience.db")

        current = Experience(
            experience_id="current-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Update parser validation and rerun regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep parser validation aligned with current tests.",
        )

        unrelated = Experience(
            experience_id="other-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Use unrelated historical approach.",
            outcome="Old result.",
            success=True,
            lesson="Unrelated project guidance.",
        )

        store.add(current)
        store.add(unrelated)

        links.save(
            ExperienceProjectLink(
                experience_id="current-exp",
                project_root=str(root),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent.repair_and_verify",),
                commit_id="current123",
            )
        )

        links.save(
            ExperienceProjectLink(
                experience_id="other-exp",
                project_root=str(root / "other"),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent.repair_and_verify",),
                commit_id="other123",
            )
        )

        planner = _planner(root)

        historical = planner._collect_experience(
            request="Fix parser validation bug",
            plan=Plan(),
            max_results=4,
            max_chars=1800,
        )

        assert "Keep parser validation aligned with current tests." in historical
        assert "Unrelated project guidance." not in historical

        prompt = planner._build_prompt(
            request="Fix parser validation bug",
            plan=Plan(),
            evidence="Current source evidence.",
        )

        assert "HISTORICAL EXPERIENCE:" in prompt
        assert "Keep parser validation aligned with current tests." in prompt
        assert "Unrelated project guidance." not in prompt
        assert "Current source code, requirements, and verification results are authoritative." in prompt
