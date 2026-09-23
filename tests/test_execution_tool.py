from tools.execution_tool import ExecutionTool


def test_execution_tool_runs_python():
    tool = ExecutionTool()

    result = tool.execute(
        'print("hello")',
        "python",
    )

    assert result.tool_name == "execute_code"
    assert result.success is True
    assert result.error is None
    assert result.result.language == "python"
    assert result.result.stdout.strip() == "hello"


def test_execution_tool_runs_javascript():
    tool = ExecutionTool()

    result = tool.execute(
        'console.log("hello")',
        "javascript",
    )

    assert result.tool_name == "execute_code"
    assert result.success is True
    assert result.result.language == "javascript"
    assert result.result.stdout.strip() == "hello"


def test_execution_tool_rejects_empty_code():
    tool = ExecutionTool()

    result = tool.execute(
        "",
        "python",
    )

    assert result.tool_name == "execute_code"
    assert result.success is False
    assert result.error == "No code supplied for execution."


def test_execution_tool_rejects_unknown_language():
    tool = ExecutionTool()

    result = tool.execute(
        "print('hello')",
        "unknown",
    )

    assert result.success is False
    assert "language is unknown" in result.error


def test_execution_tool_rejects_unsupported_language():
    tool = ExecutionTool()

    result = tool.execute(
        'puts "hello"',
        "ruby",
    )

    assert result.success is False
    assert "No execution runner" in result.error
