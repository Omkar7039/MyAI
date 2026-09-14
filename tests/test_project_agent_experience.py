from pathlib import Path
from tempfile import TemporaryDirectory

from experience.project_link import ExperienceProjectLink
from experience.project_link_store import ExperienceProjectLinkStore
from experience.store import Experience, ExperienceStore
from experience.retriever import ExperienceRetriever
from project.project_agent import ProjectAgent


def _agent(root, db):
    agent = ProjectAgent.__new__(ProjectAgent)
    agent.root = root
    agent.experience_link_store = ExperienceProjectLinkStore(db)
    agent.experience_store = ExperienceStore(db)
    agent.experience_retriever = ExperienceRetriever(
        agent.experience_store
    )
    return agent


def test_project_agent_uses_only_current_project_linked_experience():
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "MyAI"
        root.mkdir()
        data = root / "data"
        data.mkdir()
        db = data / "experience.db"

        store = ExperienceStore(db)
        links = ExperienceProjectLinkStore(db)

        current = Experience(
            experience_id="current-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Updated parser validation and reran regression tests.",
            outcome="Regression tests passed.",
            success=True,
            lesson="Keep parser validation aligned with current tests.",
        )

        unrelated = Experience(
            experience_id="other-exp",
            task="Fix parser validation bug",
            category="repair",
            action="Changed validation incorrectly.",
            outcome="Regression tests failed.",
            success=False,
            lesson="Do not reuse the unrelated project approach.",
        )

        store.add(current)
        store.add(unrelated)

        links.save(
            ExperienceProjectLink(
                experience_id="current-exp",
                project_root=str(root),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
                commit_id="current123",
            )
        )

        links.save(
            ExperienceProjectLink(
                experience_id="other-exp",
                project_root=str(root / "other-project"),
                file_paths=("agents/repair.py",),
                symbols=("RepairAgent",),
                commit_id="other123",
            )
        )

        agent = _agent(root, db)

        result = agent._collect_project_experience(
            request="Fix parser validation bug",
            files=["agents/repair.py"],
            max_results=4,
            max_chars=1800,
        )

        ids = [
            item.experience.experience_id
            for item in result["items"]
        ]

        assert "current-exp" in ids
        assert "other-exp" not in ids
        assert "current tests" in result["text"]


def test_project_agent_returns_empty_project_experience_without_links():
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / "MyAI"
        root.mkdir()
        data = root / "data"
        data.mkdir()
        db = data / "experience.db"

        store = ExperienceStore(db)

        store.add(
            Experience(
                experience_id="global-exp",
                task="Fix parser validation bug",
                category="repair",
                action="Updated parser validation.",
                outcome="Tests passed.",
                success=True,
                lesson="Verify the current tests.",
            )
        )

        agent = _agent(root, db)

        result = agent._collect_project_experience(
            request="Fix parser validation bug",
            files=["agents/repair.py"],
        )

        assert result["items"] == []
        assert "No project-linked experience was found." in result["text"]
