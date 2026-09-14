from pathlib import Path
from tempfile import TemporaryDirectory

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore
from experience.retriever import ExperienceRetriever
from experience.store import Experience, ExperienceStore
from project.project_agent import ProjectAgent


class Symbol:
    def __init__(self, name):
        self.name = name


def _agent(root, db):
    agent = ProjectAgent.__new__(ProjectAgent)
    agent.root = root
    agent.experience_link_store = ExperienceProjectLinkStore(db)
    agent.experience_store = ExperienceStore(db)
    agent.experience_retriever = ExperienceRetriever(
        agent.experience_store
    )
    return agent


def test_project_agent_prefers_symbol_linked_experience():
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "MyAI"
        root.mkdir()
        db = root / "experience.db"

        store = ExperienceStore(db)
        links = ExperienceProjectLinkStore(db)

        symbol_exp = Experience(
            experience_id="symbol-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Updated RepairAgent validation.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep RepairAgent validation aligned with current tests.",
        )

        project_exp = Experience(
            experience_id="project-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Updated generic project validation.",
            outcome="Tests passed.",
            success=True,
            lesson="Use project-level validation guidance.",
        )

        store.add(symbol_exp)
        store.add(project_exp)

        links.save(
            ExperienceProjectLink(
                experience_id="symbol-exp",
                project_root=str(root),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
                commit_id="symbol123",
            )
        )

        links.save(
            ExperienceProjectLink(
                experience_id="project-exp",
                project_root=str(root),
                file_paths=(),
                symbols=(),
                commit_id="project123",
            )
        )

        agent = _agent(root, db)

        result = agent._collect_project_experience(
            request="Fix parser validation bug",
            files=["agents/repair.py"],
            symbols=[Symbol("RepairAgent")],
            max_results=4,
            max_chars=1800,
        )

        ids = [
            item.experience.experience_id
            for item in result["items"]
        ]

        assert "symbol-exp" in ids
        assert "project-exp" in ids


def test_project_agent_ignores_symbol_link_from_other_project():
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "MyAI"
        other = Path(tmp) / "OtherProject"
        root.mkdir()
        other.mkdir()
        db = root / "experience.db"

        store = ExperienceStore(db)
        links = ExperienceProjectLinkStore(db)

        store.add(
            Experience(
                experience_id="other-symbol-exp",
                task="Fix parser validation bug",
                category="repair",
                action="Other project action.",
                outcome="Other project result.",
                success=True,
                lesson="Other project lesson.",
            )
        )

        links.save(
            ExperienceProjectLink(
                experience_id="other-symbol-exp",
                project_root=str(other),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
                commit_id="other123",
            )
        )

        agent = _agent(root, db)

        result = agent._collect_project_experience(
            request="Fix parser validation bug",
            files=["agents/repair.py"],
            symbols=[Symbol("RepairAgent")],
        )

        assert result["items"] == []
        assert "No project-linked experience was found." in result["text"]
