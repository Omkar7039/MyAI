from __future__ import annotations

from typing import Any

from core.tool_agent_context import ToolAgentContext


class ToolAgentContextFormatter:
    """
    Converts ToolAgentContext into a stable plain-Python representation.

    This component is read-only. It does not:
    - execute tools
    - modify session state
    - make decisions
    - invoke the model
    """

    def to_dict(self, context: ToolAgentContext) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        for entry in context.entries:
            entries.append(
                {
                    "request": entry.request,
                    "tool_name": entry.tool_name,
                    "success": entry.success,
                    "result": entry.result,
                    "error": entry.error,
                    "executed": entry.executed,
                    "next_action": entry.next_action,
                    "next_reason": entry.next_reason,
                }
            )

        return {
            "entries": entries,
            "step_count": context.step_count,
            "max_steps": context.max_steps,
            "status": context.status,
            "should_continue": context.should_continue,
        }

    def to_text(self, context: ToolAgentContext) -> str:
        data = self.to_dict(context)

        lines = [
            f"status: {data['status']}",
            f"step_count: {data['step_count']}",
            f"max_steps: {data['max_steps']}",
            f"should_continue: {data['should_continue']}",
        ]

        for index, entry in enumerate(data["entries"], start=1):
            lines.extend(
                [
                    f"step_{index}.request: {entry['request']}",
                    f"step_{index}.tool_name: {entry['tool_name']}",
                    f"step_{index}.success: {entry['success']}",
                    f"step_{index}.result: {entry['result']}",
                    f"step_{index}.error: {entry['error']}",
                    f"step_{index}.executed: {entry['executed']}",
                    f"step_{index}.next_action: {entry['next_action']}",
                    f"step_{index}.next_reason: {entry['next_reason']}",
                ]
            )

        return "\n".join(lines)
