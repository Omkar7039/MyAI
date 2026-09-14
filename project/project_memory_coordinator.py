from __future__ import annotations

from project.project_state import ProjectStateManager
from project.project_state_context import ProjectStateContext, ProjectStateContextBuilder


class ProjectMemoryCoordinator:
    def __init__(self, manager: ProjectStateManager | None = None):
        self.manager = manager or ProjectStateManager()
        self.context_builder = ProjectStateContextBuilder(self.manager)

    def inspect(self, context, max_chars: int = 4000) -> ProjectStateContext:
        return self.context_builder.build(
            context,
            max_chars=max_chars,
        )

    def inspect_and_record(self, context, max_chars: int = 4000):
        state = self.inspect(
            context,
            max_chars=max_chars,
        )

        snapshot = self.manager.record(context)

        return state, snapshot
