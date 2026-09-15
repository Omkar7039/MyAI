from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class TestQualityAssessment:
    valid: bool
    assertion_count: int
    statement_count: int
    import_count: int
    function_count: int
    score: float
    reasons: tuple[str, ...]

    @property
    def strong(self) -> bool:
        return self.valid and self.score >= 70.0


class TestQualityAssessor:
    def assess(self, test_code: str) -> TestQualityAssessment:
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return TestQualityAssessment(
                valid=False,
                assertion_count=0,
                statement_count=0,
                import_count=0,
                function_count=0,
                score=0.0,
                reasons=("Test code contains invalid Python syntax.",),
            )

        assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        ]

        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]

        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        ]

        statements = len(tree.body)

        reasons = []
        score = 0.0

        if assertions:
            score += min(len(assertions) * 20.0, 50.0)
            reasons.append("contains executable assertions")
        else:
            reasons.append("contains no assertions")

        if len(assertions) >= 2:
            score += 15.0
            reasons.append("covers multiple assertions")

        if imports:
            score -= min(len(imports) * 10.0, 20.0)
            reasons.append("contains imports")

        if functions:
            score -= min(len(functions) * 10.0, 20.0)
            reasons.append("contains test functions")

        if statements >= 2:
            score += 10.0
            reasons.append("contains multiple test statements")

        if statements == 1 and assertions:
            score += 5.0
            reasons.append("contains a direct assertion")

        score = max(0.0, min(score, 100.0))

        valid = bool(
            tree.body
            and assertions
        )

        if not valid:
            score = 0.0

        return TestQualityAssessment(
            valid=valid,
            assertion_count=len(assertions),
            statement_count=statements,
            import_count=len(imports),
            function_count=len(functions),
            score=score,
            reasons=tuple(reasons),
        )
