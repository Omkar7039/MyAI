from tools.execution_tool import ExecutionTool
from tools.registry import ToolRegistry


def test_registry_registers_execution_tool():
    registry = ToolRegistry()
    tool = ExecutionTool()

    registry.register(
        tool.name,
        tool.execute,
        description=tool.description,
    )

    assert registry.has("execute_code") is True

    definition = registry.get("execute_code")

    assert definition.name == "execute_code"
    assert definition.description == tool.description


def test_registry_invokes_execution_tool():
    registry = ToolRegistry()
    tool = ExecutionTool()

    registry.register(
        tool.name,
        tool.execute,
        description=tool.description,
    )

    result = registry.invoke(
        "execute_code",
        'print("registry execution")',
        "python",
    )

    assert result.tool_name == "execute_code"
    assert result.success is True
    assert result.result.language == "python"
    assert result.result.stdout.strip() == "registry execution"


def test_registry_execution_tool_preserves_failure():
    registry = ToolRegistry()
    tool = ExecutionTool()

    registry.register(
        tool.name,
        tool.execute,
        description=tool.description,
    )

    result = registry.invoke(
        "execute_code",
        "print(1 / 0)",
        "python",
    )

    assert result.tool_name == "execute_code"
    assert result.success is True
    assert result.result.success is False
    assert result.result.exit_code != 0


def test_registry_execution_tool_rejects_unsupported_language():
    registry = ToolRegistry()
    tool = ExecutionTool()

    registry.register(
        tool.name,
        tool.execute,
        description=tool.description,
    )

    result = registry.invoke(
        "execute_code",
        'puts "hello"',
        "ruby",
    )

    assert result.success is False
    assert "No execution runner" in result.error
