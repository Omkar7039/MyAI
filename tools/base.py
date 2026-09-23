from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolParameter:
    name: str
    parameter_type: str
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class ToolSchema:
    parameters: tuple[ToolParameter, ...] = ()

    def parameter_names(self) -> tuple[str, ...]:
        return tuple(
            parameter.name
            for parameter in self.parameters
        )


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None
