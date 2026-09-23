from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tools.base import ToolSchema


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., Any]
    schema: ToolSchema


class ToolRegistry:
    """
    Registry for explicitly invokable MyAI tools.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        schema: ToolSchema | None = None,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise ValueError("Tool name cannot be empty.")

        if not callable(handler):
            raise ValueError(
                f"Tool handler must be callable: {normalized}"
            )

        if normalized in self._tools:
            raise ValueError(
                f"Tool is already registered: {normalized}"
            )

        self._tools[normalized] = ToolDefinition(
            name=normalized,
            description=description,
            handler=handler,
            schema=schema or ToolSchema(),
        )

    def unregister(self, name: str) -> None:
        normalized = name.strip().lower()

        if normalized not in self._tools:
            raise ValueError(
                f"Tool is not registered: {normalized}"
            )

        del self._tools[normalized]

    def has(self, name: str) -> bool:
        return name.strip().lower() in self._tools

    def get(self, name: str) -> ToolDefinition:
        normalized = name.strip().lower()

        if normalized not in self._tools:
            raise ValueError(
                f"Tool is not registered: {normalized}"
            )

        return self._tools[normalized]

    def invoke(
        self,
        name: str,
        *args,
        **kwargs,
    ) -> Any:
        tool = self.get(name)

        # Preserve the original positional invocation contract.
        if args:
            if tool.schema.parameters:
                raise ValueError(
                    f"Tool '{tool.name}' requires keyword arguments."
                )

            return tool.handler(
                *args,
                **kwargs,
            )

        self._validate(
            tool,
            kwargs,
        )

        return tool.handler(
            **kwargs,
        )

    @staticmethod
    def _validate(
        tool: ToolDefinition,
        kwargs: dict[str, Any],
    ) -> None:
        schema = tool.schema

        if not schema.parameters:
            return

        known = {
            parameter.name
            for parameter in schema.parameters
        }

        unknown = set(kwargs) - known

        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(
                f"Unknown arguments for tool "
                f"'{tool.name}': {names}"
            )

        missing = [
            parameter.name
            for parameter in schema.parameters
            if parameter.required
            and parameter.name not in kwargs
        ]

        if missing:
            names = ", ".join(missing)
            raise ValueError(
                f"Missing required arguments for tool "
                f"'{tool.name}': {names}"
            )

        for parameter in schema.parameters:
            if parameter.name not in kwargs:
                continue

            value = kwargs[parameter.name]

            if parameter.parameter_type == "string":
                if not isinstance(value, str):
                    raise ValueError(
                        f"Argument '{parameter.name}' for tool "
                        f"'{tool.name}' must be a string."
                    )

            elif parameter.parameter_type == "integer":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(
                        f"Argument '{parameter.name}' for tool "
                        f"'{tool.name}' must be an integer."
                    )

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(
            self._tools[name]
            for name in sorted(self._tools)
        )
