import pytest

from tools.policy import (
    ToolPermission,
    ToolPolicyRegistry,
)


def test_register_and_get_policy():
    registry = ToolPolicyRegistry()

    registry.register(
        "read_file",
        ToolPermission.READ,
    )

    policy = registry.get("read_file")

    assert policy.name == "read_file"
    assert policy.permission == ToolPermission.READ


def test_tool_names_are_sorted():
    registry = ToolPolicyRegistry()

    registry.register("write_file", ToolPermission.WRITE)
    registry.register("read_file", ToolPermission.READ)

    assert registry.names() == (
        "read_file",
        "write_file",
    )


def test_tool_names_are_normalized():
    registry = ToolPolicyRegistry()

    registry.register(
        "  Read_File  ",
        ToolPermission.READ,
    )

    assert registry.has("read_file")
    assert registry.permission("READ_FILE") == ToolPermission.READ


def test_empty_tool_name_rejected():
    registry = ToolPolicyRegistry()

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register(
            "   ",
            ToolPermission.READ,
        )


def test_duplicate_policy_rejected():
    registry = ToolPolicyRegistry()

    registry.register(
        "read_file",
        ToolPermission.READ,
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            "read_file",
            ToolPermission.READ,
        )


def test_unknown_policy_rejected():
    registry = ToolPolicyRegistry()

    with pytest.raises(
        ValueError,
        match="not registered",
    ):
        registry.get("missing_tool")


def test_permission_categories():
    registry = ToolPolicyRegistry()

    registry.register(
        "read_file",
        ToolPermission.READ,
    )
    registry.register(
        "write_file",
        ToolPermission.WRITE,
    )
    registry.register(
        "delete_file",
        ToolPermission.DESTRUCTIVE,
    )
    registry.register(
        "execute_code",
        ToolPermission.EXECUTE,
    )

    assert registry.permission("read_file") == ToolPermission.READ
    assert registry.permission("write_file") == ToolPermission.WRITE
    assert registry.permission("delete_file") == ToolPermission.DESTRUCTIVE
    assert registry.permission("execute_code") == ToolPermission.EXECUTE


def test_default_policy_registry_contains_all_tools():
    from tools.policy import create_default_tool_policy_registry

    registry = create_default_tool_policy_registry()

    assert registry.names() == (
        "copy_file",
        "create_directory",
        "delete_file",
        "directory_tree",
        "edit_file",
        "execute_code",
        "file_exists",
        "file_hash",
        "get_file_info",
        "list_files",
        "move_file",
        "read_file",
        "search_files",
        "write_file",
    )


def test_default_read_only_tools():
    from tools.policy import create_default_tool_policy_registry

    registry = create_default_tool_policy_registry()

    for name in (
        "read_file",
        "list_files",
        "search_files",
        "get_file_info",
        "directory_tree",
        "file_exists",
        "file_hash",
    ):
        assert registry.permission(name) == ToolPermission.READ


def test_default_write_tools():
    from tools.policy import create_default_tool_policy_registry

    registry = create_default_tool_policy_registry()

    for name in (
        "write_file",
        "edit_file",
        "create_directory",
        "copy_file",
    ):
        assert registry.permission(name) == ToolPermission.WRITE


def test_default_destructive_tools():
    from tools.policy import create_default_tool_policy_registry

    registry = create_default_tool_policy_registry()

    for name in (
        "move_file",
        "delete_file",
    ):
        assert registry.permission(name) == ToolPermission.DESTRUCTIVE


def test_default_execute_tool():
    from tools.policy import create_default_tool_policy_registry

    registry = create_default_tool_policy_registry()

    assert (
        registry.permission("execute_code")
        == ToolPermission.EXECUTE
    )
