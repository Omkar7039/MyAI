from __future__ import annotations

from dataclasses import dataclass

from tools.code_analyzer import CodeAnalyzer
from tools.runner_manager import RunnerManager


@dataclass(frozen=True)
class DebugEvidence:
    problem: str
    language: str
    error: str | None
    static_analysis: str
    runtime: dict | None

    @property
    def runtime_available(self) -> bool:
        return self.runtime is not None

    @property
    def runtime_success(self) -> bool:
        return bool(
            self.runtime is not None
            and self.runtime.get("success", False)
        )

    @property
    def runtime_failed(self) -> bool:
        return bool(
            self.runtime is not None
            and not self.runtime.get("success", False)
        )

    @property
    def timed_out(self) -> bool:
        return bool(
            self.runtime is not None
            and self.runtime.get("timed_out", False)
        )

    @property
    def exit_code(self):
        if self.runtime is None:
            return None

        return self.runtime.get("exit_code")

    @property
    def stderr(self) -> str:
        if self.runtime is None:
            return ""

        return str(self.runtime.get("stderr", ""))

    @property
    def stdout(self) -> str:
        if self.runtime is None:
            return ""

        return str(self.runtime.get("stdout", ""))

    def render(self, max_chars: int = 4000) -> str:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")

        runtime_text = "Runtime execution was not available."

        if self.runtime is not None:
            runtime_text = (
                f"Language: {self.runtime.get('language', self.language)}\n"
                f"Success: {self.runtime.get('success', False)}\n"
                f"Exit code: {self.runtime.get('exit_code', -1)}\n"
                f"Timed out: {self.runtime.get('timed_out', False)}\n"
                f"STDOUT:\n{self.stdout}\n"
                f"STDERR:\n{self.stderr}\n"
            )

        text = (
            f"Problem:\n{self.problem}\n\n"
            f"Language:\n{self.language}\n\n"
            f"User-provided error:\n{self.error or 'None'}\n\n"
            f"Static analysis:\n{self.static_analysis}\n\n"
            f"Runtime evidence:\n{runtime_text}"
        )

        return text[:max_chars]


class DebugInvestigator:
    def __init__(
        self,
        analyzer: CodeAnalyzer | None = None,
        runner_manager: RunnerManager | None = None,
    ):
        self.analyzer = analyzer or CodeAnalyzer()
        self.runner_manager = runner_manager or RunnerManager()

    def investigate(
        self,
        problem: str,
        code: str,
        error: str | None = None,
        language: str | None = None,
    ) -> DebugEvidence:
        language = (language or "unknown").lower()

        static_analysis = self.analyzer.analyze(
            code,
            language=language,
        )

        runtime = None

        if self.runner_manager.supports(language):
            try:
                runtime = self.runner_manager.run(
                    language,
                    code,
                )
            except Exception as exc:
                runtime = {
                    "language": language,
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(exc),
                    "timed_out": False,
                }

        return DebugEvidence(
            problem=problem,
            language=language,
            error=error,
            static_analysis=static_analysis,
            runtime=runtime,
        )
