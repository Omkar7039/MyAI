from tools.runners.node_runner import NodeRunner
from tools.code_runner import PythonCodeRunner


class RunnerManager:
    def __init__(self):
        self.runners = {
            "python": PythonCodeRunner(timeout=5),
            "javascript": NodeRunner(timeout=5),
        }

    def supports(self, language: str) -> bool:
        return language.lower() in self.runners

    def run(self, language: str, code: str):
        language = language.lower()

        if language not in self.runners:
            raise ValueError(
                f"No execution runner is installed for: {language}"
            )

        runner = self.runners[language]

        if language == "python":
            result = runner.run(code)

            return {
                "language": "python",
                "success": result.exit_code == 0 and not result.timed_out,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timed_out": result.timed_out,
            }

        result = runner.run(code)

        return {
            "language": result.language,
            "success": result.success,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": result.timed_out,
        }
