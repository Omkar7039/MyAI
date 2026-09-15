from __future__ import annotations

import ast
from dataclasses import dataclass

from verification.test_quality import TestQualityAssessor


@dataclass(frozen=True)
class WeakTestAssessment:
    weak: bool
    score: float
    assertion_count: int
    duplicate_assertion_count: int
    trivial_assertion_count: int
    reasons: tuple[str, ...]


class WeakTestDetector:
    def __init__(self, quality_assessor: TestQualityAssessor | None = None):
        self.quality_assessor = quality_assessor or TestQualityAssessor()

    def detect(self, test_code: str) -> WeakTestAssessment:
        quality = self.quality_assessor.assess(test_code)

        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return WeakTestAssessment(
                weak=True,
                score=0.0,
                assertion_count=0,
                duplicate_assertion_count=0,
                trivial_assertion_count=0,
                reasons=("test code has invalid syntax",),
            )

        assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        ]

        if not assertions:
            return WeakTestAssessment(
                weak=True,
                score=0.0,
                assertion_count=0,
                duplicate_assertion_count=0,
                trivial_assertion_count=0,
                reasons=("test contains no assertions",),
            )

        fingerprints = [
            ast.dump(
                node.test,
                annotate_fields=True,
                include_attributes=False,
            )
            for node in assertions
        ]

        duplicate_count = len(fingerprints) - len(set(fingerprints))

        trivial_count = sum(
            1
            for node in assertions
            if self._is_trivial_assertion(node.test)
        )

        reasons = list(quality.reasons)
        score = quality.score

        if len(assertions) < 2:
            score -= 20.0
            reasons.append("test contains fewer than two assertions")

        if duplicate_count:
            score -= min(duplicate_count * 15.0, 30.0)
            reasons.append("test contains duplicate assertions")

        if trivial_count:
            score -= min(trivial_count * 15.0, 30.0)
            reasons.append("test contains trivial assertions")

        score = max(0.0, min(100.0, score))

        weak = (
            score < 70.0
            or duplicate_count > 0
            or trivial_count > 0
            or len(assertions) < 2
        )

        return WeakTestAssessment(
            weak=weak,
            score=score,
            assertion_count=len(assertions),
            duplicate_assertion_count=duplicate_count,
            trivial_assertion_count=trivial_count,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _is_trivial_assertion(expression: ast.expr) -> bool:
        if isinstance(expression, ast.Constant):
            return True

        if isinstance(expression, ast.Compare):
            if isinstance(expression.left, ast.Constant) and all(
                isinstance(comparator, ast.Constant)
                for comparator in expression.comparators
            ):
                return True

        return False
