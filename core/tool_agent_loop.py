from __future__ import annotations

from dataclasses import dataclass

from core.tool_agent_step import ToolAgentStep, ToolAgentStepResult


@dataclass(frozen=True)
class ToolAgentLoopResult:
    steps: tuple[ToolAgentStepResult, ...]
    completed: bool
    stopped: bool
    max_steps_reached: bool


class ToolAgentLoop:
    """
    Runs bounded ToolAgentStep iterations.

    The loop itself does not select or execute tools.
    ToolAgentStep remains responsible for one complete step.
    """

    def __init__(
        self,
        step: ToolAgentStep,
        *,
        max_steps: int = 5,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        self._step = step
        self._max_steps = max_steps

    def run(self, request: str) -> ToolAgentLoopResult:
        results: list[ToolAgentStepResult] = []

        current_request = request

        for _ in range(self._max_steps):
            result = self._step.run(current_request)
            results.append(result)

            if result.next_decision.action == "complete":
                return ToolAgentLoopResult(
                    steps=tuple(results),
                    completed=True,
                    stopped=False,
                    max_steps_reached=False,
                )

            if result.next_decision.action == "stop":
                return ToolAgentLoopResult(
                    steps=tuple(results),
                    completed=False,
                    stopped=True,
                    max_steps_reached=False,
                )

            if result.next_decision.action == "continue":
                continue

        return ToolAgentLoopResult(
            steps=tuple(results),
            completed=False,
            stopped=False,
            max_steps_reached=True,
        )
