from __future__ import annotations

from dataclasses import dataclass

from agents.debug_hypothesis import DebugHypothesis


@dataclass(frozen=True)
class RankedDebugHypothesis:
    hypothesis: DebugHypothesis
    score: int
    reasons: tuple[str, ...]


class DebugHypothesisRanker:
    def rank(self, hypotheses, evidence=None):
        ranked = []

        for hypothesis in hypotheses:
            score = int(hypothesis.confidence)
            reasons = [f"base confidence: {hypothesis.confidence}"]

            if evidence is not None:
                stderr = evidence.stderr.lower()
                analysis = evidence.static_analysis.lower()
                problem = evidence.problem.lower()

                description = hypothesis.description.lower()

                if (
                    "name" in description
                    and ("nameerror" in stderr or "undefined name" in analysis)
                ):
                    score += 20
                    reasons.append("runtime/static evidence matches")

                if (
                    "type" in description
                    and ("typeerror" in stderr or "type" in analysis)
                ):
                    score += 20
                    reasons.append("runtime/static evidence matches")

                if (
                    "syntax" in description
                    and ("syntaxerror" in stderr or "syntax" in analysis)
                ):
                    score += 20
                    reasons.append("runtime/static evidence matches")

                if (
                    "intended behavior" in description
                    and any(
                        term in problem
                        for term in (
                            "wrong result",
                            "incorrect result",
                            "wrong behavior",
                            "incorrect behavior",
                            "should return",
                        )
                    )
                ):
                    score += 20
                    reasons.append("user requirement matches")

            score = min(score, 100)

            ranked.append(
                RankedDebugHypothesis(
                    hypothesis=hypothesis,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                -item.hypothesis.confidence,
                item.hypothesis.description,
            )
        )

        return ranked
