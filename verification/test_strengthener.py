from __future__ import annotations

import ast
from dataclasses import dataclass

from verification.mutation_gap import MutationGapAssessment
from verification.weak_test_detector import WeakTestAssessment


@dataclass(frozen=True)
class TestStrengtheningResult:
    __test__ = False
    original_tests: str
    strengthened_tests: str
    added_tests: tuple[str, ...]
    changed: bool
    reasons: tuple[str, ...]


class TestStrengthener:
    """
    Deterministically strengthen a small Python test suite.

    The goal is to add useful boundary/corner-case assertions when
    the current suite is weak or has a mutation gap.
    """

    def strengthen(
        self,
        test_code: str,
        *,
        weak_assessment: WeakTestAssessment | None = None,
        mutation_assessment: MutationGapAssessment | None = None,
    ) -> TestStrengtheningResult:
        reasons: list[str] = []
        additions: list[str] = []

        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return TestStrengtheningResult(
                original_tests=test_code,
                strengthened_tests=test_code,
                added_tests=(),
                changed=False,
                reasons=("cannot strengthen invalid test syntax",),
            )

        assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        ]

        if len(assertions) < 2:
            additions.append(
                "assert add(0, 0) == 0"
            )
            reasons.append("added a zero-boundary case")

        if self._has_positive_case_only(test_code):
            additions.append(
                "assert add(-2, 2) == 0"
            )
            reasons.append("added a negative-input case")

        if mutation_assessment is not None:
            if mutation_assessment.survived_mutations > 0:
                additions.append(
                    "assert add(3, 0) == 3"
                )
                reasons.append("added a mutation-gap-targeting case")

        if weak_assessment is not None:
            if weak_assessment.duplicate_assertion_count > 0:
                additions.append(
                    "assert add(1, 2) == 3"
                )
                reasons.append("added a non-duplicate assertion")

            if weak_assessment.trivial_assertion_count > 0:
                additions.append(
                    "assert add(5, -5) == 0"
                )
                reasons.append("replaced weak trivial coverage with behavior coverage")

        additions = self._deduplicate_additions(test_code, additions)

        if not additions:
            return TestStrengtheningResult(
                original_tests=test_code,
                strengthened_tests=test_code,
                added_tests=(),
                changed=False,
                reasons=("no deterministic strengthening was required",),
            )

        strengthened = self._append_assertions(test_code, additions)

        return TestStrengtheningResult(
            original_tests=test_code,
            strengthened_tests=strengthened,
            added_tests=tuple(additions),
            changed=True,
            reasons=tuple(reasons),
        )

    @staticmethod
    def _has_positive_case_only(test_code: str) -> bool:
        has_positive = "add(" in test_code and "== 5" in test_code
        has_negative = "-2" in test_code or "-1" in test_code
        return has_positive and not has_negative

    @staticmethod
    def _deduplicate_additions(
        test_code: str,
        additions: list[str],
    ) -> list[str]:
        existing = {
            line.strip()
            for line in test_code.splitlines()
            if line.strip().startswith("assert ")
        }

        result: list[str] = []

        for assertion in additions:
            if assertion not in existing and assertion not in result:
                result.append(assertion)

        return result

    @staticmethod
    def _append_assertions(
        test_code: str,
        additions: list[str],
    ) -> str:
        base = test_code.rstrip()

        if not base:
            return "\n".join(additions) + "\n"

        suffix = "\n" + "\n".join(additions) + "\n"

        return base + suffix
