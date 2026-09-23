from core.tool_decision_engine import ToolDecisionEngine


def test_decides_read_file():
    engine = ToolDecisionEngine()

    result = engine.decide("Read the file config.py")

    assert result.decision is not None
    assert result.decision.tool_name == "read_file"
    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "config.py"


def test_decides_list_files():
    engine = ToolDecisionEngine()

    result = engine.decide("List files in src")

    assert result.decision is not None
    assert result.decision.tool_name == "list_files"
    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "src"


def test_decides_file_exists():
    engine = ToolDecisionEngine()

    result = engine.decide(
        "Check if the file config.py exists"
    )

    assert result.decision is not None
    assert result.decision.tool_name == "file_exists"
    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "config.py"


def test_decides_delete_file():
    engine = ToolDecisionEngine()

    result = engine.decide("Delete the file old.py")

    assert result.decision is not None
    assert result.decision.tool_name == "delete_file"
    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "old.py"


def test_decides_create_directory():
    engine = ToolDecisionEngine()

    result = engine.decide(
        "Create directory src/utils"
    )

    assert result.decision is not None
    assert result.decision.tool_name == "create_directory"
    assert result.arguments is not None
    assert result.arguments.arguments["path"] == "src/utils"


def test_unknown_request_returns_no_decision():
    engine = ToolDecisionEngine()

    result = engine.decide(
        "Explain how Python decorators work"
    )

    assert result.decision is None
    assert result.arguments is None


def test_empty_request_returns_no_decision():
    engine = ToolDecisionEngine()

    result = engine.decide("   ")

    assert result.decision is None
    assert result.arguments is None


def test_result_is_deterministic():
    engine = ToolDecisionEngine()

    first = engine.decide("Read the file config.py")
    second = engine.decide("Read the file config.py")

    assert first == second
