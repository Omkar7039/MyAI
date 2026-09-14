from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationResult:
    passed: bool
    syntax_passed: bool
    runtime_passed: bool
    behavior_passed: Optional[bool]
    score: float
    reason: str
    details: str


class VerificationEngine:
    def verify(
        self,
        runner_manager,
        language: str,
        code: str,
        expected_stdout: Optional[str] = None,
        expected_exit_code: int = 0,
    ) -> VerificationResult:

        language = language.lower()

        if not runner_manager.supports(language):
            return VerificationResult(
                passed=False,
                syntax_passed=False,
                runtime_passed=False,
                behavior_passed=None,
                score=0.0,
                reason="No execution runner is available.",
                details=f"Unsupported verification language: {language}",
            )

        try:
            result = runner_manager.run(language, code)
        except Exception as exc:
            return VerificationResult(
                passed=False,
                syntax_passed=False,
                runtime_passed=False,
                behavior_passed=None,
                score=0.0,
                reason="Execution could not be performed.",
                details=str(exc),
            )

        runtime_passed = (
            result["exit_code"] == expected_exit_code
            and not result["timed_out"]
        )

        syntax_passed = runtime_passed or result["exit_code"] != 0

        if not runtime_passed:
            return VerificationResult(
                passed=False,
                syntax_passed=syntax_passed,
                runtime_passed=False,
                behavior_passed=False,
                score=0.0,
                reason="Runtime verification failed.",
                details=(
                    f"Exit code: {result['exit_code']}\n"
                    f"Timed out: {result['timed_out']}\n"
                    f"STDOUT:\n{result['stdout']}\n"
                    f"STDERR:\n{result['stderr']}"
                ),
            )

        if expected_stdout is None:
            return VerificationResult(
                passed=True,
                syntax_passed=True,
                runtime_passed=True,
                behavior_passed=None,
                score=0.70,
                reason="Runtime verification passed; behavior was not specified.",
                details=(
                    "Program executed successfully, but no expected output "
                    "or regression test was supplied."
                ),
            )

        actual = result["stdout"].strip()
        expected = expected_stdout.strip()

        behavior_passed = actual == expected

        if behavior_passed:
            return VerificationResult(
                passed=True,
                syntax_passed=True,
                runtime_passed=True,
                behavior_passed=True,
                score=1.0,
                reason="Runtime and behavioral verification passed.",
                details=(
                    f"Expected output:\n{expected}\n\n"
                    f"Actual output:\n{actual}"
                ),
            )

        return VerificationResult(
            passed=False,
            syntax_passed=True,
            runtime_passed=True,
            behavior_passed=False,
            score=0.70,
            reason="Runtime passed but behavioral verification failed.",
            details=(
                f"Expected output:\n{expected}\n\n"
                f"Actual output:\n{actual}"
            ),
        )
