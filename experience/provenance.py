from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperienceProvenance:
    source: str
    workflow: str
    evidence: tuple[str, ...]
    verified: bool

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be empty")

        if not self.workflow.strip():
            raise ValueError("workflow must not be empty")

        cleaned = tuple(
            item.strip()
            for item in self.evidence
            if item.strip()
        )

        object.__setattr__(
            self,
            "evidence",
            cleaned,
        )

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)

    @property
    def evidence_text(self) -> str:
        return ", ".join(self.evidence)

    def to_metadata(self) -> dict[str, object]:
        return {
            "source": self.source,
            "workflow": self.workflow,
            "evidence": list(self.evidence),
            "verified": self.verified,
        }
