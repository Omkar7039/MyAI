from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    EXECUTE = "execute"


@dataclass(frozen=True)
class ToolPolicy:
    name: str
    permission: ToolPermission


class ToolPolicyRegistry:
    """
    Central classification of MyAI tools.
    """

    def __init__(self):
        self._policies: dict[str, ToolPolicy] = {}

    def register(
        self,
        name: str,
        permission: ToolPermission,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise ValueError("Tool name cannot be empty.")

        if normalized in self._policies:
            raise ValueError(
                f"Tool policy is already registered: {normalized}"
            )

        self._policies[normalized] = ToolPolicy(
            name=normalized,
            permission=permission,
        )

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._policies

    def get(self, name: str) -> ToolPolicy:
        normalized = name.strip().lower()

        if normalized not in self._policies:
            raise ValueError(
                f"Tool policy is not registered: {normalized}"
            )

        return self._policies[normalized]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._policies))

    def permission(self, name: str) -> ToolPermission:
        return self.get(name).permission


DEFAULT_TOOL_POLICIES = {
    "read_file": ToolPermission.READ,
    "list_files": ToolPermission.READ,
    "search_files": ToolPermission.READ,
    "get_file_info": ToolPermission.READ,
    "directory_tree": ToolPermission.READ,
    "file_exists": ToolPermission.READ,
    "file_hash": ToolPermission.READ,

    "write_file": ToolPermission.WRITE,
    "edit_file": ToolPermission.WRITE,
    "create_directory": ToolPermission.WRITE,
    "copy_file": ToolPermission.WRITE,

    "move_file": ToolPermission.DESTRUCTIVE,
    "delete_file": ToolPermission.DESTRUCTIVE,

    "execute_code": ToolPermission.EXECUTE,
}


def create_default_tool_policy_registry() -> ToolPolicyRegistry:
    """
    Create the standard policy registry for MyAI's built-in tools.
    """
    registry = ToolPolicyRegistry()

    for name, permission in DEFAULT_TOOL_POLICIES.items():
        registry.register(name, permission)

    return registry
