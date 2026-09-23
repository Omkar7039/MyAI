from pathlib import Path

from core.orchestrator import Orchestrator
from core.tool_plan_executor import ToolPlanExecutor


def test_executor_runs_read_file(tmp_path):
    target = tmp_path / "config.py"
    target.write_text("VALUE = 42\n")

    orchestrator = Orchestrator()
    orchestrator.workspace.root = Path(tmp_path).resolve()

    executor = ToolPlanExecutor(orchestrator)

    result = executor.execute(
        "Read the file config.py"
    )

    assert result.executed is True
    assert result.execution.success is True
    assert result.execution.result["content"] == "VALUE = 42\n"


def test_executor_runs_list_files(tmp_path):
    (tmp_path / "a.py").write_text("a")
    (tmp_path / "b.py").write_text("b")

    orchestrator = Orchestrator()
    orchestrator.workspace.root = Path(tmp_path).resolve()

    executor = ToolPlanExecutor(orchestrator)

    result = executor.execute(
        "List files in ."
    )

    assert result.executed is True
    assert result.execution.success is True


def test_executor_does_not_run_unknown_request():
    orchestrator = Orchestrator()
    executor = ToolPlanExecutor(orchestrator)

    result = executor.execute(
        "Explain Python decorators"
    )

    assert result.executed is False
    assert result.execution is None


def test_executor_preserves_policy_guard(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.tool_policy_guard.allow_destructive = False

    executor = ToolPlanExecutor(orchestrator)

    result = executor.execute(
        "Delete the file missing.py"
    )

    assert result.executed is False or result.execution is None
