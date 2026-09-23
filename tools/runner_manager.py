from tools.code_runner import PythonCodeRunner
from tools.runners.node_runner import NodeRunner


class RunnerManager:
    """
    Select and execute the appropriate language runner.
    """

    def __init__(self):
        self.runners = {
            "python": PythonCodeRunner(timeout=5),
            "javascript": NodeRunner(timeout=5),
        }

    def supports(self, language: str) -> bool:
        return language.lower() in self.runners

    def run(self, language: str, code: str):
        normalized = language.lower()

        if normalized not in self.runners:
            raise ValueError(
                f"No execution runner is installed for: {language}"
            )

        return self.runners[normalized].run(code)
