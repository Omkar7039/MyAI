from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebugHypothesis:
    description: str
    evidence: tuple[str, ...]
    confidence: int


class DebugHypothesisGenerator:
    def generate(self, evidence) -> list[DebugHypothesis]:
        hypotheses = []

        stderr = evidence.stderr.lower()
        problem = evidence.problem.lower()
        analysis = evidence.static_analysis.lower()

        if (
            "nameerror" in stderr
            or "undefined name" in analysis
            or "undefined variable" in analysis
        ):
            hypotheses.append(
                DebugHypothesis(
                    description="A variable or name is referenced before it is defined.",
                    evidence=(
                        "runtime reports NameError",
                        "static analysis reports an undefined name",
                    ),
                    confidence=95,
                )
            )

        if (
            "typeerror" in stderr
            or "incompatible type" in analysis
        ):
            hypotheses.append(
                DebugHypothesis(
                    description="An operation is using an incompatible value type.",
                    evidence=(
                        "runtime reports TypeError",
                        "static analysis reports a type incompatibility",
                    ),
                    confidence=90,
                )
            )

        if (
            "syntaxerror" in stderr
            or "syntax" in analysis
        ):
            hypotheses.append(
                DebugHypothesis(
                    description="The source contains invalid syntax.",
                    evidence=(
                        "runtime or static analysis reports a syntax problem",
                    ),
                    confidence=98,
                )
            )

        semantic_signals = (
            "wrong result",
            "incorrect result",
            "incorrect behavior",
            "wrong behavior",
            "logical error",
            "logic error",
            "should return",
            "expected",
            "bug",
        )

        if any(signal in problem for signal in semantic_signals):
            hypotheses.append(
                DebugHypothesis(
                    description="The implementation does not match the intended behavior.",
                    evidence=(
                        "user problem describes incorrect or unexpected behavior",
                    ),
                    confidence=80,
                )
            )

        if evidence.runtime_failed and not hypotheses:
            hypotheses.append(
                DebugHypothesis(
                    description="The program has a runtime failure that requires further investigation.",
                    evidence=(
                        f"runtime exited with code {evidence.exit_code}",
                    ),
                    confidence=50,
                )
            )

        unique = {}
        for hypothesis in hypotheses:
            unique[hypothesis.description] = hypothesis

        return sorted(
            unique.values(),
            key=lambda item: (
                -item.confidence,
                item.description,
            ),
        )
