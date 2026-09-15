from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebugFailureClassification:
    category: str
    confidence: int
    reasons: tuple[str, ...]


class DebugFailureClassifier:
    def classify(self, evidence) -> DebugFailureClassification:
        stderr = evidence.stderr.lower()
        problem = evidence.problem.lower()
        analysis = evidence.static_analysis.lower()

        if evidence.timed_out:
            return DebugFailureClassification(
                category="timeout",
                confidence=100,
                reasons=("runtime execution timed out",),
            )

        if "syntaxerror" in stderr or "syntax" in analysis:
            return DebugFailureClassification(
                category="syntax",
                confidence=98,
                reasons=("syntax failure reported by runtime or analysis",),
            )

        if "nameerror" in stderr or "undefined name" in analysis:
            return DebugFailureClassification(
                category="name",
                confidence=95,
                reasons=("undefined name evidence detected",),
            )

        if "typeerror" in stderr or "type" in analysis:
            return DebugFailureClassification(
                category="type",
                confidence=90,
                reasons=("type-related runtime or static evidence detected",),
            )

        if (
            "assertionerror" in stderr
            or "test failed" in problem
            or "tests failed" in problem
        ):
            return DebugFailureClassification(
                category="assertion/test",
                confidence=90,
                reasons=("test/assertion failure evidence detected",),
            )

        if any(
            term in stderr
            for term in (
                "modulenotfounderror",
                "filenotfounderror",
                "permissionerror",
                "connectionerror",
            )
        ):
            return DebugFailureClassification(
                category="environment/tool",
                confidence=85,
                reasons=("environment or tool failure evidence detected",),
            )

        if any(
            term in problem
            for term in (
                "wrong result",
                "incorrect result",
                "wrong behavior",
                "incorrect behavior",
                "logical error",
                "logic error",
            )
        ):
            return DebugFailureClassification(
                category="semantic",
                confidence=80,
                reasons=("user reported incorrect behavior",),
            )

        if evidence.runtime_failed:
            return DebugFailureClassification(
                category="unknown",
                confidence=40,
                reasons=(
                    f"runtime failed with exit code {evidence.exit_code}",
                ),
            )

        return DebugFailureClassification(
            category="none",
            confidence=100,
            reasons=("no failure evidence detected",),
        )
