from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropertyCase:
    name: str
    expression: str
    description: str


class PropertyExpansionEngine:
    """
    Generate deterministic property checks for common Python operations.

    This phase only generates executable property expressions.
    Execution remains the responsibility of the existing verification
    infrastructure.
    """

    def expand(
        self,
        function_name: str,
        operation: str,
    ) -> tuple[PropertyCase, ...]:
        normalized = operation.strip().lower()

        if normalized == "add":
            return self._add_properties(function_name)

        if normalized == "sort":
            return self._sort_properties(function_name)

        if normalized == "reverse":
            return self._reverse_properties(function_name)

        return ()

    @staticmethod
    def _add_properties(function_name: str) -> tuple[PropertyCase, ...]:
        return (
            PropertyCase(
                name="add_commutative",
                expression=(
                    f"{function_name}(2, 7) == "
                    f"{function_name}(7, 2)"
                ),
                description="addition is commutative",
            ),
            PropertyCase(
                name="add_zero_left",
                expression=(
                    f"{function_name}(0, 7) == 7"
                ),
                description="zero is the left identity",
            ),
            PropertyCase(
                name="add_zero_right",
                expression=(
                    f"{function_name}(7, 0) == 7"
                ),
                description="zero is the right identity",
            ),
            PropertyCase(
                name="add_negative_pair",
                expression=(
                    f"{function_name}(-7, 7) == 0"
                ),
                description="opposite values cancel",
            ),
        )

    @staticmethod
    def _sort_properties(function_name: str) -> tuple[PropertyCase, ...]:
        return (
            PropertyCase(
                name="sort_ordered",
                expression=(
                    f"{function_name}([3, 1, 2]) == [1, 2, 3]"
                ),
                description="sorting produces ascending order",
            ),
            PropertyCase(
                name="sort_already_sorted",
                expression=(
                    f"{function_name}([1, 2, 3]) == [1, 2, 3]"
                ),
                description="already sorted input remains unchanged",
            ),
            PropertyCase(
                name="sort_duplicates",
                expression=(
                    f"{function_name}([2, 1, 2]) == [1, 2, 2]"
                ),
                description="sorting preserves duplicates",
            ),
            PropertyCase(
                name="sort_empty",
                expression=(
                    f"{function_name}([]) == []"
                ),
                description="empty input remains empty",
            ),
        )

    @staticmethod
    def _reverse_properties(
        function_name: str,
    ) -> tuple[PropertyCase, ...]:
        return (
            PropertyCase(
                name="reverse_basic",
                expression=(
                    f"{function_name}([1, 2, 3]) == [3, 2, 1]"
                ),
                description="reverse changes element order",
            ),
            PropertyCase(
                name="reverse_twice",
                expression=(
                    f"{function_name}("
                    f"{function_name}([1, 2, 3])"
                    f") == [1, 2, 3]"
                ),
                description="reversing twice restores the original order",
            ),
            PropertyCase(
                name="reverse_single",
                expression=(
                    f"{function_name}([1]) == [1]"
                ),
                description="single-element input is unchanged",
            ),
            PropertyCase(
                name="reverse_empty",
                expression=(
                    f"{function_name}([]) == []"
                ),
                description="empty input remains empty",
            ),
        )
