from core.orchestrator import Orchestrator


def test_orchestrator_exposes_tool_decision():
    orchestrator = Orchestrator()

    result = orchestrator.decide_tool(
        "Read the file config.py"
    )

    assert result.decision is not None
    assert result.decision.tool_name == "read_file"


def test_orchestrator_tool_decision_includes_arguments():
    orchestrator = Orchestrator()

    result = orchestrator.decide_tool(
        "List files in src"
    )

    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "src"


def test_orchestrator_does_not_decide_for_normal_question():
    orchestrator = Orchestrator()

    result = orchestrator.decide_tool(
        "Explain Python decorators"
    )

    assert result.decision is None
    assert result.arguments is None
