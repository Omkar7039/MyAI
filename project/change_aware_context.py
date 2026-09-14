from __future__ import annotations

from dataclasses import dataclass

from project.project_retriever import ProjectRetriever


@dataclass(frozen=True)
class ChangeAwareContext:
    files: tuple[dict, ...]
    changed_files: tuple[str, ...]
    text: str
    max_chars: int


class ChangeAwareContextAssembler:
    def __init__(self, retriever: ProjectRetriever | None = None):
        self.retriever = retriever or ProjectRetriever()

    def assemble(
        self,
        files,
        request: str,
        changed_files=(),
        max_chars: int = 6000,
    ) -> ChangeAwareContext:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")

        evidence = self.retriever.read_changed_files(
            files,
            request,
            changed_files=changed_files,
        )

        blocks = []

        for item in evidence:
            block = (
                f"FILE: {item['file']}\n"
                f"SCORE: {item.get('score', 0)}\n"
                f"REASONS: {', '.join(item.get('reasons', []))}\n"
                f"SOURCE:\n{item['source']}"
            )
            blocks.append(block)

        text = "\n\n".join(blocks)

        if len(text) > max_chars:
            text = text[:max_chars].rstrip()

        return ChangeAwareContext(
            files=tuple(evidence),
            changed_files=tuple(str(path) for path in changed_files),
            text=text,
            max_chars=max_chars,
        )
