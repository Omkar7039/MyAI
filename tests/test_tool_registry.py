import pytest

from tools.registry import ToolRegistry


from tools.base import ToolParameter, ToolSchema
def test_registry_registers_and_finds_tool():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda value: value,
        description="Return the supplied value.",
    )

    assert registry.has("echo") is True
    assert registry.has("missing") is False

    tool = registry.get("echo")

    assert tool.name == "echo"
    assert tool.description == "Return the supplied value."


def test_registry_invokes_tool():
    registry = ToolRegistry()

    registry.register(
        "add",
        lambda a, b: a + b,
    )

    result = registry.invoke("add", 2, 3)

    assert result == 5


def test_registry_normalizes_tool_names():
    registry = ToolRegistry()

    registry.register(
        "  Echo  ",
        lambda: "ok",
    )

    assert registry.has("echo") is True
    assert registry.invoke(" ECHO ") == "ok"


def test_registry_rejects_duplicate_tool():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda: "first",
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(
            "echo",
            lambda: "second",
        )


def test_registry_rejects_unknown_tool():
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="not registered"):
        registry.get("missing")


def test_registry_rejects_empty_tool_name():
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register(
            "   ",
            lambda: None,
        )


def test_registry_lists_tools_deterministically():
    registry = ToolRegistry()

    registry.register("zeta", lambda: None)
    registry.register("alpha", lambda: None)
    registry.register("beta", lambda: None)

    assert registry.names() == (
        "alpha",
        "beta",
        "zeta",
    )


def test_registry_rejects_non_callable_handler():
    registry = ToolRegistry()

    with pytest.raises(
        ValueError,
        match="handler must be callable",
    ):
        registry.register(
            "invalid",
            "not callable",
        )


def test_registry_normalizes_lookup_names():
    registry = ToolRegistry()

    registry.register(
        "  Echo  ",
        lambda: "ok",
    )

    assert registry.get(" ECHO ").name == "echo"


def test_registry_unregisters_tool():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda: "ok",
    )

    registry.unregister(" ECHO ")

    assert registry.has("echo") is False


def test_registry_rejects_unregistering_unknown_tool():
    registry = ToolRegistry()

    with pytest.raises(
        ValueError,
        match="not registered",
    ):
        registry.unregister("missing")


def test_registry_schema_requires_keyword_arguments():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda value: value,
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="requires keyword arguments",
    ):
        registry.invoke("echo", "hello")


def test_registry_schema_rejects_missing_argument():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda **kwargs: kwargs["value"],
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Missing required arguments",
    ):
        registry.invoke("echo")


def test_registry_schema_rejects_unknown_argument():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda **kwargs: kwargs["value"],
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Unknown arguments",
    ):
        registry.invoke(
            "echo",
            value="hello",
            extra="bad",
        )


def test_registry_schema_validates_string_type():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda **kwargs: kwargs["value"],
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                ),
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="must be a string",
    ):
        registry.invoke(
            "echo",
            value=123,
        )


def test_registry_schema_allows_valid_arguments():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda **kwargs: kwargs["value"],
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                ),
            ),
        ),
    )

    assert registry.invoke(
        "echo",
        value="hello",
    ) == "hello"


def test_registry_definition_exposes_schema():
    registry = ToolRegistry()

    registry.register(
        "echo",
        lambda value: value,
        description="Echo a string.",
        schema=ToolSchema(
            parameters=(
                ToolParameter(
                    name="value",
                    parameter_type="string",
                    description="Value to echo.",
                ),
            ),
        ),
    )

    definition = registry.get("echo")

    assert definition.name == "echo"
    assert definition.description == "Echo a string."
    assert definition.schema.parameter_names() == ("value",)
    assert definition.schema.parameters[0].description == "Value to echo."


def test_registry_definitions_are_sorted():
    registry = ToolRegistry()

    registry.register("zeta", lambda: None)
    registry.register("alpha", lambda: None)
    registry.register("beta", lambda: None)

    assert tuple(
        definition.name
        for definition in registry.definitions()
    ) == ("alpha", "beta", "zeta")
