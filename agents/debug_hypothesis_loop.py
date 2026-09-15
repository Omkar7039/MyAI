from __future__ import annotations

from dataclasses import dataclass

from agents.debug_hypothesis import DebugHypothesisGenerator
from agents.debug_hypothesis_ranker import DebugHypothesisRanker
from agents.debug_hypothesis_verifier import DebugHypothesisVerifier


@dataclass(frozen=True)
class DebugHypothesisLoopResult:
    selected: object | None
    attempts: tuple[object, ...]
    stopped_safely: bool


class DebugHypothesisLoop:
    def __init__(
        self,
        generator: DebugHypothesisGenerator | None = None,
        ranker: DebugHypothesisRanker | None = None,
        verifier: DebugHypothesisVerifier | None = None,
    ):
        self.generator = generator or DebugHypothesisGenerator()
        self.ranker = ranker or DebugHypothesisRanker()
        self.verifier = verifier or DebugHypothesisVerifier()

    def run(self, evidence) -> DebugHypothesisLoopResult:
        hypotheses = self.generator.generate(evidence)

        ranked = self.ranker.rank(
            hypotheses,
            evidence,
        )

        attempts = []

        for candidate in ranked:
            verification = self.verifier.verify(
                candidate.hypothesis,
                evidence,
            )

            attempts.append(verification)

            if verification.verified:
                return DebugHypothesisLoopResult(
                    selected=candidate.hypothesis,
                    attempts=tuple(attempts),
                    stopped_safely=False,
                )

        return DebugHypothesisLoopResult(
            selected=None,
            attempts=tuple(attempts),
            stopped_safely=True,
        )
