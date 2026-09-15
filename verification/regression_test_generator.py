from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class RegressionTest:
    test_code: str
    function_name: str
    description: str
    source: str
    expected: str


class RegressionTestGenerator:
    """
    Generate small deterministic regression tests from a known
    input/output failure case.

    The generator does not invoke the language model. It is intended
    to preserve confirmed bug cases after a repair.
    """

    def generate(
        self,
        source_code: str,
        function_name: str,
        arguments: tuple[object, ...],
        expected: object,
        description: str = "",
    ) -> RegressionTest:
        self._validate_function(source_code, function_name)

        call = self._format_call(function_name, arguments)
        expected_code = self._format_value(expected)

        test_code = (
            f"def test_regression_{function_name}():\n"
            f"    assert {call} == {expected_code}\n"
        )

        return RegressionTest(
            test_code=test_code,
            function_name=function_name,
            description=description or (
                f"Regression test for {function_name}"
            ),
            source=source_code,
            expected=expected_code,
        )

    @staticmethod
    def _validate_function(source_code: str, function_name: str) -> None:
        try:
            tree = ast.parse(source_code)
        except SyntaxError as exc:
            raise ValueError(
                "source_code contains invalid Python syntax"
            ) from exc

        functions = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        if function_name not in functions:
            raise ValueError(
                f"function {function_name!r} was not found in source_code"
            )

    @staticmethod
    def _format_call(
        function_name: str,
        arguments: tuple[object, ...],
    ) -> str:
        values = ", ".join(
            RegressionTestGenerator._format_value(argument)
            for argument in arguments
        )
        return f"{function_name}({values})"

    @staticmethod
    def _format_value(value: object) -> str:
        return repr(value)
