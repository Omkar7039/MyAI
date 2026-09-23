from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from tools.base import ToolResult


class ToolResultNormalizer:
    """
    Normalize tool outputs into a predictable dictionary structure.
    """

    @staticmethod
    def normalize(result: Any) -> dict[str, Any]:
        if isinstance(result, ToolResult):
            return {
                "tool_name": result.tool_name,
                "success": result.success,
                "result": ToolResultNormalizer._convert(result.result),
                "error": result.error,
            }

        return {
            "tool_name": None,
            "success": True,
            "result": ToolResultNormalizer._convert(result),
            "error": None,
        }

    @staticmethod
    def _convert(value: Any) -> Any:
        if is_dataclass(value) and not isinstance(value, type):
            return {
                key: ToolResultNormalizer._convert(item)
                for key, item in asdict(value).items()
            }

        if isinstance(value, dict):
            return {
                str(key): ToolResultNormalizer._convert(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [
                ToolResultNormalizer._convert(item)
                for item in value
            ]

        if isinstance(value, set):
            return sorted(
                ToolResultNormalizer._convert(item)
                for item in value
            )

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)
