from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HypothesisVerification:
    hypothesis: object
    verified: bool
    score: int
    evidence: tuple[str, ...]
    reason: str


class DebugHypothesisVerifier:
    def verify(self, hypothesis, evidence) -> HypothesisVerification:
        description = (
            getattr(hypothesis, "description", "")
            or ""
        ).lower()

        stderr = evidence.stderr.lower()
        analysis = evidence.static_analysis.lower()
        problem = evidence.problem.lower()

        matched = []
        score = 0

        if "name" in description:
            if "nameerror" in stderr:
                matched.append("runtime NameError matches hypothesis")
                score += 60

            if "undefined name" in analysis:
                matched.append("static undefined-name evidence matches")
                score += 30

        if "type" in description:
            if "typeerror" in stderr:
                matched.append("runtime TypeError matches hypothesis")
                score += 60

            if "type" in analysis:
                matched.append("static type evidence matches")
                score += 30

        if "syntax" in description:
            if "syntaxerror" in stderr:
                matched.append("runtime SyntaxError matches hypothesis")
                score += 60

            if "syntax" in analysis:
                matched.append("static syntax evidence matches")
                score += 30

        if "intended behavior" in description:
            if any(
                term in problem
                for term in (
                    "wrong result",
                    "incorrect result",
                    "wrong behavior",
                    "incorrect behavior",
                    "should return",
                )
            ):
                matched.append("user requirement matches hypothesis")
                score += 80

        verified = score >= 60

        if verified:
            reason = "Hypothesis is supported by available evidence."
        else:
            reason = "Insufficient evidence to verify the hypothesis."

        return HypothesisVerification(
            hypothesis=hypothesis,
            verified=verified,
            score=min(score, 100),
            evidence=tuple(matched),
            reason=reason,
        )
