from __future__ import annotations

from dataclasses import dataclass

from project.project_state import ProjectStateManager, ProjectStateSummary


@dataclass(frozen=True)
class ProjectStateContext:
    state: ProjectStateSummary
    max_chars: int = 4000

    @property
    def current_snapshot(self):
        return self.state.current

    @property
    def previous_snapshot(self):
        return self.state.previous

    @property
    def changed_files(self):
        return self.state.changed_files

    def render(self) -> str:
        text = self.state.render()

        if len(text) > self.max_chars:
            text = text[: self.max_chars].rstrip()

        return text


class ProjectStateContextBuilder:
    def __init__(self, manager: ProjectStateManager | None = None):
        self.manager = manager or ProjectStateManager()

    def build(self, context, max_chars: int = 4000):
        if max_chars < 1:
            raise ValueError('max_chars must be >= 1')

        state = self.manager.summarize(context)

        return ProjectStateContext(
            state=state,
            max_chars=max_chars,
        )
