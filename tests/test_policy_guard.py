import pytest

from tools.policy import (
    ToolPermission,
    create_default_tool_policy_registry,
)
from tools.policy_guard import (
    ToolExecutionMode,
    ToolPolicyGuard,
)


def test_read_tools_are_allowed():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    assert guard.is_allowed("read_file") is True
    assert guard.is_allowed("search_files") is True


def test_write_tools_are_allowed_by_default():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    assert guard.is_allowed("write_file") is True
    assert guard.is_allowed("edit_file") is True


def test_destructive_tools_are_blocked_by_default():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    assert guard.is_allowed("delete_file") is False
    assert guard.is_allowed("move_file") is False


def test_execute_tools_are_blocked_by_default():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    assert guard.is_allowed("execute_code") is False


def test_destructive_tools_can_be_enabled():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(
        registry,
        allow_destructive=True,
    )

    assert guard.is_allowed("delete_file") is True
    assert guard.is_allowed("move_file") is True


def test_execute_tools_can_be_enabled():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(
        registry,
        allow_execute=True,
    )

    assert guard.is_allowed("execute_code") is True


def test_write_tools_can_be_disabled():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(
        registry,
        allow_write=False,
    )

    assert guard.is_allowed("write_file") is False
    assert guard.is_allowed("edit_file") is False


def test_blocked_tool_raises_permission_error():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    with pytest.raises(
        PermissionError,
        match="blocked by the tool policy",
    ):
        guard.check("delete_file")


def test_allowed_tool_does_not_raise():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    guard.check("read_file")


def test_unknown_tool_policy_is_rejected():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    with pytest.raises(
        ValueError,
        match="not registered",
    ):
        guard.check("missing_tool")


def test_permission_message_identifies_category():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    with pytest.raises(
        PermissionError,
        match="destructive",
    ):
        guard.check("delete_file")


def test_restricted_mode_is_default():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(registry)

    assert guard.mode == ToolExecutionMode.RESTRICTED
    assert guard.is_allowed("read_file") is True
    assert guard.is_allowed("write_file") is True
    assert guard.is_allowed("delete_file") is False
    assert guard.is_allowed("execute_code") is False


def test_permissive_mode_allows_all_tool_categories():
    registry = create_default_tool_policy_registry()
    guard = ToolPolicyGuard(
        registry,
        mode=ToolExecutionMode.PERMISSIVE,
    )

    assert guard.is_allowed("read_file") is True
    assert guard.is_allowed("write_file") is True
    assert guard.is_allowed("delete_file") is True
    assert guard.is_allowed("execute_code") is True


def test_explicit_flags_override_mode_defaults():
    registry = create_default_tool_policy_registry()

    guard = ToolPolicyGuard(
        registry,
        mode=ToolExecutionMode.RESTRICTED,
        allow_destructive=True,
        allow_execute=True,
    )

    assert guard.is_allowed("delete_file") is True
    assert guard.is_allowed("execute_code") is True
