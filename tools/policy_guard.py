from __future__ import annotations

from enum import Enum

from tools.policy import (
    ToolPermission,
    ToolPolicyRegistry,
)


class ToolExecutionMode(str, Enum):
    """
    Controls which categories of tools may execute.
    """

    PERMISSIVE = "permissive"
    RESTRICTED = "restricted"


class ToolPolicyGuard:
    """
    Enforce execution permissions for registered tools.
    """

    def __init__(
        self,
        policy_registry: ToolPolicyRegistry,
        *,
        mode: ToolExecutionMode = ToolExecutionMode.RESTRICTED,
        allow_write: bool | None = None,
        allow_destructive: bool | None = None,
        allow_execute: bool | None = None,
    ):
        self.policy_registry = policy_registry
        self.mode = mode

        if mode == ToolExecutionMode.PERMISSIVE:
            defaults = {
                "write": True,
                "destructive": True,
                "execute": True,
            }
        else:
            defaults = {
                "write": True,
                "destructive": False,
                "execute": False,
            }

        self.allow_write = (
            defaults["write"]
            if allow_write is None
            else allow_write
        )

        self.allow_destructive = (
            defaults["destructive"]
            if allow_destructive is None
            else allow_destructive
        )

        self.allow_execute = (
            defaults["execute"]
            if allow_execute is None
            else allow_execute
        )

    def is_allowed(self, tool_name: str) -> bool:
        permission = self.policy_registry.permission(tool_name)

        if permission == ToolPermission.READ:
            return True

        if permission == ToolPermission.WRITE:
            return self.allow_write

        if permission == ToolPermission.DESTRUCTIVE:
            return self.allow_destructive

        if permission == ToolPermission.EXECUTE:
            return self.allow_execute

        return False

    def check(self, tool_name: str) -> None:
        permission = self.policy_registry.permission(tool_name)

        if self.is_allowed(tool_name):
            return

        raise PermissionError(
            f"Tool '{tool_name.strip().lower()}' is blocked by "
            f"the tool policy ({permission.value})."
        )
