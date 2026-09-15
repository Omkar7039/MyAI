from core.model import LocalModel
from agents.repair import RepairAgent
from tools.code_analyzer import CodeAnalyzer
from tools.runner_manager import RunnerManager
from agents.debug_investigation import DebugInvestigator


class DebugAgent:
    def __init__(self, model=None):
        self.model = model or LocalModel()
        self.analyzer = CodeAnalyzer()
        self.runner_manager = RunnerManager()
        self.investigator = DebugInvestigator(
            analyzer=self.analyzer,
            runner_manager=self.runner_manager,
        )
        self.repair_agent = RepairAgent(self.model)

    def analyze(
        self,
        problem,
        code=None,
        error=None,
        language=None,
        auto_repair=True,
    ):
        if not code:
            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": (
                            "Analyze this debugging problem and explain the "
                            "likely cause and solution:\n\n" + problem
                        ),
                    }
                ],
                max_tokens=512,
            )

        language = (language or "unknown").lower()

        investigation = self.investigator.investigate(
            problem=problem,
            code=code,
            error=error,
            language=language,
        )

        analysis = investigation.static_analysis
        runtime = investigation.runtime

        runtime_text = "Runtime execution was not available."

        if runtime is not None:
            runtime_text = (
                f"Language: {runtime['language']}\n"
                f"Success: {runtime['success']}\n"
                f"Exit code: {runtime['exit_code']}\n"
                f"Timed out: {runtime['timed_out']}\n"
                f"STDOUT:\n{runtime['stdout']}\n"
                f"STDERR:\n{runtime['stderr']}\n"
            )

        diagnosis_prompt = (
            "You are MyAI's debugging agent.\n\n"
            "Analyze the supplied source code using the runtime evidence "
            "and static analysis.\n"
            "Do not invent errors that are not supported by the evidence.\n"
            "Identify the root cause, explain it clearly, and propose the "
            "smallest correct fix.\n\n"
            f"User problem:\n{problem}\n\n"
            f"Language:\n{language}\n\n"
            f"User-provided error:\n{error or 'None'}\n\n"
            f"Static analysis:\n{analysis}\n\n"
            f"Runtime evidence:\n{runtime_text}\n\n"
            f"Source code:\n```{language}\n{code}\n```\n"
        )

        diagnosis = self.model.ask(
            [
                {
                    "role": "user",
                    "content": diagnosis_prompt,
                }
            ],
            max_tokens=768,
        )

        result = diagnosis

        if (
            auto_repair
            and language == "python"
            and runtime is not None
            and not runtime["timed_out"]
            and (
                runtime["exit_code"] != 0
                or self._needs_semantic_repair(
                    problem=problem,
                    diagnosis=diagnosis,
                )
            )
        ):
            repair_problem = (
                f"Original user request:\n{problem}\n\n"
                f"Debugging diagnosis:\n{diagnosis}\n\n"
                "Repair the code according to the intended behavior "
                "identified by the diagnosis. Do not preserve behavior "
                "that the diagnosis identifies as incorrect."
            )

            repair_result = self.repair_agent.repair_and_verify(
                code=code,
                problem=repair_problem,
            )

            repair_success = bool(
                repair_result.get("success", False)
            )

            repaired_code = (
                repair_result.get("code")
                or repair_result.get("fixed_code")
                or repair_result.get("repaired_code")
            )

            attempts = repair_result.get(
                "attempts",
                [],
            )

            reason = repair_result.get(
                "reason",
                "No additional repair details were returned.",
            )

            if repair_success and repaired_code:
                result += (
                    "\n\n"
                    "=== AUTOMATIC REPAIR ===\n"
                    "Verification: PASS\n\n"
                    "Corrected code:\n"
                    f"```python\n{repaired_code}\n```\n\n"
                    f"Attempts: {attempts}\n"
                    f"Reason: {reason}"
                )
            elif repair_success:
                result += (
                    "\n\n"
                    "=== AUTOMATIC REPAIR ===\n"
                    "Repair reported success, but no corrected code "
                    "was returned.\n"
                    f"Attempts: {attempts}\n"
                    f"Reason: {reason}"
                )
            else:
                result += (
                    "\n\n"
                    "=== AUTOMATIC REPAIR ===\n"
                    "Automatic repair could not be verified.\n"
                    f"Reason: {reason}\n"
                    f"Attempts: {attempts}"
                )

        elif runtime is not None and runtime["success"]:
            result += (
                "\n\n"
                "=== RUNTIME VERIFICATION ===\n"
                f"{language} execution completed successfully."
            )

        return result

    def _needs_semantic_repair(
        self,
        problem: str,
        diagnosis: str,
    ) -> bool:
        text = (
            problem
            + "\n"
            + diagnosis
        ).lower()

        signals = (
            "logical error",
            "logic error",
            "semantic error",
            "incorrect behavior",
            "wrong behavior",
            "does not perform",
            "intended to",
            "should return",
            "should add",
            "should subtract",
            "should multiply",
            "should divide",
            "incorrectly",
            "wrong result",
            "bug",
            "root cause",
            "proposed fix",
            "smallest correct fix",
        )

        return any(
            signal in text
            for signal in signals
        )
