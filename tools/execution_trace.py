from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolExecutionTrace:
    tool_name: str
    success: bool
    duration_ms: float
    error: str | None = None


class ToolExecutionTracer:
    """
    Records lightweight execution metadata for tool invocations.
    """

    def __init__(self):
        self._traces: list[ToolExecutionTrace] = []

    def record(
        self,
        tool_name: str,
        success: bool,
        duration_ms: float,
        error: str | None = None,
    ) -> ToolExecutionTrace:
        trace = ToolExecutionTrace(
            tool_name=tool_name,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self._traces.append(trace)
        return trace

    def traces(self) -> tuple[ToolExecutionTrace, ...]:
        return tuple(self._traces)

    def clear(self) -> None:
        self._traces.clear()

    def time(self):
        return time.perf_counter()
