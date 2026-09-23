from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.tool_agent_session import ToolAgentSession
from core.tool_agent_step import ToolAgentStepResult


@dataclass(frozen=True)
class ToolAgentContextEntry:
    request: str
    tool_name: str | None
    success: bool
    result: Any
    error: str | None
    executed: bool
    next_action: str
    next_reason: str


@dataclass(frozen=True)
class ToolAgentContext:
    entries: tuple[ToolAgentContextEntry, ...]
    step_count: int
    max_steps: int
    status: str
    should_continue: bool


class ToolAgentContextBuilder:
    """
    Builds an immutable, model-ready view of a ToolAgentSession.

    This component only reads session state. It never executes tools,
    modifies session history, or makes a next-step decision.
    """

    def build(self, session: ToolAgentSession) -> ToolAgentContext:
        entries: list[ToolAgentContextEntry] = []

        for request, step_result in zip(
            session.request_history,
            session.history,
        ):
            observation = step_result.observation

            entries.append(
                ToolAgentContextEntry(
                    request=request,
                    tool_name=observation.tool_name,
                    success=observation.success,
                    result=observation.result,
                    error=observation.error,
                    executed=observation.executed,
                    next_action=step_result.next_decision.action,
                    next_reason=step_result.next_decision.reason,
                )
            )

        return ToolAgentContext(
            entries=tuple(entries),
            step_count=session.step_count,
            max_steps=session.max_steps,
            status=session.status,
            should_continue=session.should_continue,
        )
