from pathlib import Path
from tempfile import TemporaryDirectory

from project.change_aware_context import ChangeAwareContextAssembler
from project.project_agent import ProjectAgent
from project.project_history import ProjectHistoryQuery
from project.project_memory import ProjectMemoryStore
from project.project_memory_health import ProjectMemoryHealthChecker
from project.project_memory_policy import AutomaticProjectMemoryUpdater
from project.project_memory_reconcile import ProjectMemoryReconciler
from project.project_state import ProjectStateManager


def make_real_project(root):
    (root / "repair.py").write_text(
        "def repair():\n    return 1\n",
        encoding="utf-8",
    )
    (root / "utils.py").write_text(
        "def helper():\n    return 2\n",
        encoding="utf-8",
    )


def make_context(root):
    from types import SimpleNamespace

    files = [
        SimpleNamespace(
            path="repair.py",
            size=(root / "repair.py").stat().st_size,
            language="python",
        ),
        SimpleNamespace(
            path="utils.py",
            size=(root / "utils.py").stat().st_size,
            language="python",
        ),
    ]

    return SimpleNamespace(
        root=str(root),
        repository_report=SimpleNamespace(
            files=files,
            total_files=len(files),
            total_bytes=sum(item.size for item in files),
        ),
        code_index=SimpleNamespace(symbols=[]),
        dependency_graph=SimpleNamespace(nodes={}),
        call_graph=SimpleNamespace(nodes={}, edges=[]),
    )


def test_advanced_project_memory_end_to_end():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        make_real_project(root)

        store = ProjectMemoryStore(
            root / "project-memory.db"
        )
        manager = ProjectStateManager(store)
        updater = AutomaticProjectMemoryUpdater(
            ProjectMemoryReconciler(store)
        )

        first_context = make_context(root)

        first_reconciliation, first_decision = updater.update(
            first_context
        )

        assert first_reconciliation.stored is None
        assert first_decision.should_update is True
        assert len(store.history(root)) == 1

        (root / "repair.py").write_text(
            "def repair():\n    return 42\n",
            encoding="utf-8",
        )

        second_context = make_context(root)

        second_reconciliation = updater.reconciler.inspect(
            second_context
        )

        assert second_reconciliation.stored is not None
        assert second_reconciliation.needs_update is True
        assert len(store.history(root)) == 1


        agent = ProjectAgent.__new__(ProjectAgent)
        agent.project_memory_store = store
        agent.project_state_manager = manager

        from project.project_state_context import (
            ProjectStateContextBuilder,
        )

        agent.project_state_context = (
            ProjectStateContextBuilder(manager)
        )

        agent_state = agent._collect_project_state(
            second_context,
            max_chars=1800,
        )

        assert agent_state["previous_snapshot"] is not None
        assert agent_state["current_snapshot"] is not None
        assert "repair.py" in agent_state["text"]


        second_reconciliation, second_decision = updater.update(
            second_context
        )

        assert second_decision.should_update is True
        assert len(store.history(root)) == 2

        history = ProjectHistoryQuery(store).latest(
            str(root)
        )

        assert len(history) == 2
        assert history[0].changed is True
        assert history[0].files

        assembler = ChangeAwareContextAssembler()
        assembler.retriever.root = root

        context = assembler.assemble(
            ["repair.py", "utils.py"],
            request="repair bug",
            changed_files=["repair.py"],
        )

        assert context.files
        assert context.files[0]["file"] == "repair.py"
        assert "def repair():" in context.text

        health = ProjectMemoryHealthChecker(store).check(
            str(root)
        )

        assert health.healthy is True
        assert health.snapshot_count == 2
        assert health.latest_available is True
        assert health.manifests_valid is True
