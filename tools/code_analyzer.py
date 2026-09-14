import ast
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    language: str
    syntax_valid: bool
    syntax_error: str
    details: str


class CodeAnalyzer:
    """
    Static analysis foundation.

    Currently Python gets real AST validation.
    Other languages are passed through for model-based analysis.
    """

    def analyze(
        self,
        code: str,
        language: str,
    ) -> AnalysisResult:

        if language != "python":
            return AnalysisResult(
                language=language,
                syntax_valid=True,
                syntax_error="",
                details=(
                    f"Static parser for {language} is not installed yet. "
                    "Model-based analysis will be used."
                ),
            )

        try:
            tree = ast.parse(code)

            functions = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            classes = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            ]

            details = (
                f"Python AST valid. "
                f"Functions: {functions or 'none'}. "
                f"Classes: {classes or 'none'}."
            )

            return AnalysisResult(
                language="python",
                syntax_valid=True,
                syntax_error="",
                details=details,
            )

        except SyntaxError as exc:
            return AnalysisResult(
                language="python",
                syntax_valid=False,
                syntax_error=(
                    f"{exc.msg} "
                    f"(line {exc.lineno}, column {exc.offset})"
                ),
                details="Python AST parsing failed.",
            )
