from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from core.tool_agent_step import ToolAgentStep, ToolAgentStepResult


SessionStatus = Literal[
    "active",
    "completed",
    "stopped",
    "limit_reached",
]


@dataclass(frozen=True)
class ToolAgentSessionSnapshot:
    step_count: int
    max_steps: int
    should_continue: bool
    last_result: ToolAgentStepResult | None
    status: SessionStatus


class ToolAgentSession:
    """
    Maintains bounded tool-agent session state.

    A session step is always explicit. This class never loops or
    automatically executes another tool.
    """

    def __init__(
        self,
        executor: Callable[[str], object],
        max_steps: int = 10,
    ) -> None:
        if isinstance(max_steps, bool) or not isinstance(max_steps, int):
            raise TypeError("max_steps must be an integer.")

        if max_steps < 1:
            raise ValueError("max_steps must be at least 1.")

        self._step = ToolAgentStep(executor)
        self._max_steps = max_steps
        self._history: list[ToolAgentStepResult] = []
        self._requests: list[str] = []

    @property
    def step_count(self) -> int:
        return len(self._history)

    @property
    def max_steps(self) -> int:
        return self._max_steps

    @property
    def history(self) -> tuple[ToolAgentStepResult, ...]:
        return tuple(self._history)

    @property
    def last_result(self) -> ToolAgentStepResult | None:
        if not self._history:
            return None
        return self._history[-1]

    @property
    def request_history(self) -> tuple[str, ...]:
        return tuple(self._requests)

    @property
    def last_request(self) -> str | None:
        if not self._requests:
            return None
        return self._requests[-1]

    @property
    def status(self) -> SessionStatus:
        if self.step_count >= self.max_steps:
            return "limit_reached"

        result = self.last_result

        if result is None:
            return "active"

        action = result.next_decision.action

        if action == "complete":
            return "completed"

        if action == "stop":
            return "stopped"

        return "active"

    @property
    def should_continue(self) -> bool:
        result = self.last_result

        if result is None:
            return False

        return (
            result.next_decision.action == "continue"
            and self.step_count < self.max_steps
        )

    def step(self, request: str) -> ToolAgentStepResult:
        if self.step_count >= self.max_steps:
            raise RuntimeError(
                "Maximum tool-agent session steps reached."
            )

        result = self._step.run(request)
        self._history.append(result)
        self._requests.append(request)

        return result

    def snapshot(self) -> ToolAgentSessionSnapshot:
        return ToolAgentSessionSnapshot(
            step_count=self.step_count,
            max_steps=self.max_steps,
            should_continue=self.should_continue,
            last_result=self.last_result,
            status=self.status,
        )

    def reset(self) -> None:
        self._history.clear()
        self._requests.clear()
