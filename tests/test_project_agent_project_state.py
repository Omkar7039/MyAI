from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from project.project_agent import ProjectAgent
from project.project_memory import ProjectMemoryStore
from project.project_state import ProjectStateManager
from project.project_state_context import ProjectStateContextBuilder


def make_context(root, files):
    infos = [
        SimpleNamespace(
            path=path,
            size=size,
            language="python",
        )
        for path, size in files
    ]

    return SimpleNamespace(
        root=str(root),
        repository_report=SimpleNamespace(
            files=infos,
            total_files=len(infos),
            total_bytes=sum(size for _, size in files),
        ),
        code_index=SimpleNamespace(symbols=[]),
        dependency_graph=SimpleNamespace(nodes={}),
        call_graph=SimpleNamespace(nodes={}, edges=[]),
    )


def make_agent(root):
    agent = ProjectAgent.__new__(ProjectAgent)

    store = ProjectMemoryStore(
        root / "project-memory.db"
    )
    manager = ProjectStateManager(store)

    agent.project_memory_store = store
    agent.project_state_manager = manager
    agent.project_state_context = ProjectStateContextBuilder(
        manager
    )

    return agent


def test_project_agent_collects_project_state():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        agent = make_agent(root)

        first = make_context(
            root,
            [("main.py", 100)],
        )

        agent.project_state_manager.record(first)

        current = make_context(
            root,
            [
                ("main.py", 150),
                ("new.py", 50),
            ],
        )

        state = agent._collect_project_state(
            current,
            max_chars=1800,
        )

        assert state["current_snapshot"] is not None
        assert state["previous_snapshot"] is not None
        assert state["changed_files"] == (
            "main.py",
            "new.py",
        )
        assert "Modified: main.py" in state["text"]
        assert "Added: new.py" in state["text"]


def test_project_agent_project_state_is_bounded():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        agent = make_agent(root)

        context = make_context(
            root,
            [
                (f"file{i}.py", i + 100)
                for i in range(30)
            ],
        )

        state = agent._collect_project_state(
            context,
            max_chars=120,
        )

        assert len(state["text"]) <= 120


def test_project_agent_project_state_is_present_in_evidence():
    with TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        agent = make_agent(root)

        agent._find_relevant_symbols = lambda context, request: []
        agent._add_flow_symbols = (
            lambda context, request, symbols: symbols
        )
        agent._dedupe_symbols = lambda symbols: symbols
        agent._find_relevant_files = (
            lambda context, request, symbols: []
        )
        agent.retriever = SimpleNamespace(
            read_related_sources=lambda symbols, files: {
                "symbols": [],
                "files": [],
            }
        )
        agent._apply_source_budget = (
            lambda bundle, max_chars: bundle
        )
        agent._collect_relationships = (
            lambda context, symbols: []
        )
        agent._collect_memory = (
            lambda request, max_results, max_chars: {
                "text": "",
            }
        )
        agent._build_verified_flow = (
            lambda context, request: {}
        )
        agent._collect_project_experience = (
            lambda request, files, symbols, max_results, max_chars: {
                "text": "",
                "items": [],
            }
        )

        context = make_context(
            root,
            [("main.py", 100)],
        )

        evidence = agent._collect_evidence(
            context,
            "main",
        )

        assert "project_state" in evidence
        assert evidence["project_state"]["current_snapshot"] is not None
