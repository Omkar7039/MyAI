import ast
import re

from experience.recorder import ExperienceRecorder
from experience.retriever import ExperienceRetriever
from experience.planner import ExperiencePlanner
from experience.provenance import ExperienceProvenance
from agents.repair_strategy import RepairStrategyExecutor
from tools.runner_manager import RunnerManager
from verification.test_generator import TestGenerator
from verification.mutation_engine import MutationEngine
from verification.test_strengthener import TestStrengthener
from verification.property_engine import PropertyEngine


class RepairAgent:
    MAX_ATTEMPTS = 3
    MIN_MUTATION_SCORE = 0.80

    def __init__(self, model):
        self.model = model

        self.runner_manager = RunnerManager()

        self.test_generator = TestGenerator(
            model
        )

        self.mutation_engine = MutationEngine(
            self.runner_manager
        )

        self.test_strengthener = TestStrengthener(
            model,
            self.mutation_engine,
        )

        self.property_engine = PropertyEngine(
            self.runner_manager
        )

        self.experience_recorder = ExperienceRecorder()
        self.experience_retriever = ExperienceRetriever()
        self.experience_planner = ExperiencePlanner(
            self.experience_retriever,
            max_chars=1600,
        )

        self.strategy_executor = RepairStrategyExecutor()

    def extract_code(
        self,
        response: str,
        language: str = "python",
    ):
        match = re.search(
            rf"```{language}\s*(.*?)```",
            response,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return self.clean_repaired_code(
                match.group(1).strip()
            )

        match = re.search(
            r"```\s*(.*?)```",
            response,
            re.DOTALL,
        )

        if match:
            return self.clean_repaired_code(
                match.group(1).strip()
            )

        return None

    def clean_repaired_code(self, code: str):
        markers = [
            "# ===== MYAI REGRESSION TESTS =====",
            "# ===== MYAI GENERATED REGRESSION TESTS =====",
            "# ===== MYAI INTERNAL REGRESSION TESTS =====",
            "# REGRESSION TESTS",
            "# GENERATED TESTS",
        ]

        for marker in markers:
            if marker in code:
                code = code.split(
                    marker,
                    1,
                )[0].rstrip()

        cleaned = []

        for line in code.splitlines():
            stripped = line.strip()

            if stripped == "print('__MYAI_TESTS_PASSED__')":
                continue

            if stripped == "print('__MYAI_PROPERTIES_PASSED__')":
                continue

            cleaned.append(line)

        code = "\n".join(cleaned).strip()

        if not code:
            return None

        try:
            ast.parse(code)
        except SyntaxError:
            return None

        return code

    def generate_repair(
        self,
        code: str,
        problem: str,
        failure: str,
        tests: str,
        properties=None,
    ):
        property_text = (
            "\nNo additional deterministic properties are available.\n"
            if not properties
            else
            "\nAdditional deterministic properties:\n"
            + "\n".join(properties)
            + "\n"
        )

        experience_guidance = self.experience_planner.plan(
            problem,
        )

        experience_text = (
            "\n"
            + experience_guidance.text
            + "\n"
        )

        prompt = (
            "You are MyAI's automatic Python repair agent.\n\n"
            "Repair the SOURCE CODE according to the USER REQUIREMENT.\n"
            "The regression tests and properties represent intended "
            "behavior.\n"
            "The repaired code must satisfy them.\n\n"
            "IMPORTANT:\n"
            "Do not modify, weaken, remove, or bypass the tests.\n"
            "Do not merely suppress an error.\n"
            "Preserve intended behavior.\n\n"
            "OUTPUT RULES:\n"
            "Return ONLY complete repaired Python source code.\n"
            "Do NOT include regression tests.\n"
            "Do NOT include assert statements from the tests.\n"
            "Do NOT include test runners.\n"
            "Do NOT include explanations outside the code block.\n\n"
            f"USER REQUIREMENT:\n{problem}\n\n"
            f"FAILURE:\n{failure}\n\n"
            f"REGRESSION TESTS:\n"
            f"```python\n{tests}\n```\n"
            f"{property_text}\n"
            f"{experience_text}"
            f"SOURCE CODE:\n"
            f"```python\n{code}\n```\n"
        )

        return self.model.ask(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=768,
        )

    def _build_experience_context(
        self,
        problem,
        max_chars=1600,
    ):
        """
        Build a small advisory experience context.

        Historical experience never overrides current source,
        current tests, or current verification results.
        """
        successful = self.experience_retriever.successful(
            problem,
            limit=3,
        )

        warnings = self.experience_retriever.warnings(
            problem,
            limit=3,
        )

        sections = [
            "ADVISORY HISTORICAL EXPERIENCE:",
            "This information comes from previous attempts.",
            "It is NOT authoritative. Current source code and "
            "current regression/verification results take priority.",
        ]

        used = sum(len(item) for item in sections)

        if successful:
            sections.append("\nSUCCESSFUL PRECEDENTS:")

            for item in successful:
                experience = item.experience

                block = (
                    f"- Task: {experience.task}\n"
                    f"  Action: {experience.action}\n"
                    f"  Outcome: {experience.outcome}\n"
                    f"  Lesson: {experience.lesson}\n"
                )

                if used + len(block) > max_chars:
                    break

                sections.append(block)
                used += len(block)
        else:
            sections.append(
                "\nNo successful historical precedent was found."
            )

        if warnings and used < max_chars:
            sections.append("\nFAILED ATTEMPTS / WARNINGS:")

            for item in warnings:
                experience = item.experience

                block = (
                    f"- Task: {experience.task}\n"
                    f"  Previous action: {experience.action}\n"
                    f"  Outcome: {experience.outcome}\n"
                    f"  Warning: {experience.lesson}\n"
                )

                if used + len(block) > max_chars:
                    break

                sections.append(block)
                used += len(block)

        sections.append(
            "\nDo not copy an historical solution blindly. "
            "Verify every change against the current source and tests.\n\n"
        )

        result = "\n".join(sections)

        return result[:max_chars]

    def run_tests(
        self,
        code: str,
        tests: str,
    ):
        program = (
            code.rstrip()
            + "\n\n"
            + "# ===== MYAI INTERNAL REGRESSION TESTS =====\n"
            + tests.rstrip()
            + "\n"
            + "print('__MYAI_TESTS_PASSED__')\n"
        )

        return self.runner_manager.run(
            "python",
            program,
        )

    def run_properties(
        self,
        code: str,
        problem: str,
    ):
        return self.property_engine.verify(
            source_code=code,
            problem=problem,
        )

    def mutation_check(
        self,
        code: str,
        tests: str,
    ):
        return self.mutation_engine.evaluate_test_strength(
            source_code=code,
            tests=tests,
        )

    def strengthen_tests(
        self,
        code: str,
        tests: str,
    ):
        return self.test_strengthener.strengthen(
            source_code=code,
            tests=tests,
        )

    def _acceptance_check(
        self,
        code: str,
        problem: str,
        tests: str,
    ):
        test_result = self.run_tests(
            code,
            tests,
        )

        if not test_result["success"]:
            return {
                "accepted": False,
                "tests_passed": False,
                "mutation_passed": False,
                "property_passed": False,
                "property_available": False,
                "mutation": None,
                "properties": None,
                "failure": (
                    f"Regression tests failed.\n"
                    f"Exit code: {test_result['exit_code']}\n"
                    f"STDOUT:\n{test_result['stdout']}\n"
                    f"STDERR:\n{test_result['stderr']}"
                ),
            }

        mutation = self.mutation_check(
            code=code,
            tests=tests,
        )

        mutation_passed = (
            mutation["score"]
            >= self.MIN_MUTATION_SCORE
        )

        properties = self.run_properties(
            code=code,
            problem=problem,
        )

        property_available = properties["available"]

        # No applicable properties = N/A, not failure.
        property_passed = (
            properties["passed"]
            if property_available
            else True
        )

        accepted = (
            test_result["success"]
            and mutation_passed
            and property_passed
        )

        failure_parts = []

        if not mutation_passed:
            failure_parts.append(
                "Mutation verification failed: "
                f"{mutation['reason']}"
            )

        if property_available and not property_passed:
            failure_parts.append(
                "Property verification failed: "
                f"{properties['reason']}"
            )

        return {
            "accepted": accepted,
            "tests_passed": True,
            "mutation_passed": mutation_passed,
            "property_passed": property_passed,
            "property_available": property_available,
            "mutation": mutation,
            "properties": properties,
            "failure": "\n".join(failure_parts),
        }

    def _record_experience(
        self,
        problem,
        result,
    ):
        """
        Record only the final verified outcome.

        Historical experience is advisory and never determines
        whether a repair is accepted.
        """
        success = bool(
            result.get("success")
            and result.get("verified")
        )

        attempts = result.get("attempts") or []

        if success:
            action = (
                f"Repair completed after "
                f"{len(attempts)} candidate attempt(s)."
            )

            outcome = (
                "Final regression, mutation, and applicable "
                "property verification passed."
            )

            lesson = (
                "A repair candidate satisfied the current "
                "verification gates for this task."
            )
        else:
            action = (
                f"Repair workflow completed after "
                f"{len(attempts)} candidate attempt(s)."
            )

            outcome = result.get(
                "reason",
                "Repair did not pass final verification.",
            )

            lesson = (
                "Treat this outcome as a warning. Recheck the "
                "current source, requirements, and verification "
                "results before repeating the approach."
            )

        evidence = []

        if result.get("behavior_verified"):
            evidence.append("regression behavior verified")

        if result.get("mutation_verified"):
            evidence.append("mutation verification passed")

        if (
            result.get("property_available")
            and result.get("property_verified")
        ):
            evidence.append("property verification passed")

        provenance = ExperienceProvenance(
            source="repair",
            workflow="repair_and_verify",
            evidence=tuple(evidence),
            verified=success,
        )

        try:
            self.experience_recorder.record_repair(
                task=problem,
                action=action,
                outcome=outcome,
                success=success,
                lesson=lesson,
                provenance=provenance,
            )
        except Exception:
            # Experience memory must never break repair.
            pass

    def repair_and_verify(
        self,
        code: str,
        problem: str,
        expected_stdout=None,
        strategy: str = RepairStrategyExecutor.STANDARD,
    ):
        strategy_decision = self.strategy_executor.resolve(strategy)

        # ---------------------------------------------------------
        # 1. Generate intent-based regression tests.
        # ---------------------------------------------------------
        tests = self.test_generator.generate_python_tests(
            code=code,
            problem=problem,
        )

        if not tests:
            result = {
                "success": False,
                "verified": False,
                "behavior_verified": False,
                "mutation_verified": False,
                "property_verified": False,
                "property_available": False,
                "code": code,
                "fixed_code": code,
                "repaired_code": code,
                "attempts": [],
                "reason": (
                    "Could not establish a valid "
                    "intent-based regression test suite."
                ),
                "tests": None,
                "mutation": None,
                "properties": None,
                "strengthening": None,
            }

            result["strategy"] = strategy_decision.applied
            result["requested_strategy"] = strategy_decision.requested
            result["strategy_fallback"] = strategy_decision.fallback
            result["strategy_reason"] = strategy_decision.reason

            self._record_experience(problem, result)
            return result

        # ---------------------------------------------------------
        # 2. Test original code.
        # ---------------------------------------------------------
        initial = self.run_tests(
            code,
            tests,
        )

        current_code = code
        attempts = []

        # ---------------------------------------------------------
        # 3. If original code fails, repair it.
        # ---------------------------------------------------------
        if not initial["success"]:
            failure = (
                f"Exit code: {initial['exit_code']}\n"
                f"STDOUT:\n{initial['stdout']}\n"
                f"STDERR:\n{initial['stderr']}"
            )

            repaired = False

            for attempt_number in range(
                1,
                self.MAX_ATTEMPTS + 1,
            ):
                # Give the repair model the currently known properties.
                current_properties = self.property_engine.infer_properties(
                    source_code=current_code,
                    problem=problem,
                )

                response = self.generate_repair(
                    code=current_code,
                    problem=problem,
                    failure=failure,
                    tests=tests,
                    properties=current_properties,
                )

                repaired_code = self.extract_code(
                    response,
                    language="python",
                )

                if not repaired_code:
                    attempts.append(
                        {
                            "attempt": attempt_number,
                            "runtime_passed": False,
                            "tests_passed": False,
                            "mutation_passed": False,
                            "property_passed": False,
                            "reason": (
                                "No valid standalone Python "
                                "source was returned."
                            ),
                        }
                    )

                    failure = (
                        "Return complete Python source only. "
                        "Do not include tests or explanations."
                    )

                    continue

                current_code = repaired_code

                test_result = self.run_tests(
                    current_code,
                    tests,
                )

                if not test_result["success"]:
                    attempts.append(
                        {
                            "attempt": attempt_number,
                            "runtime_passed": False,
                            "tests_passed": False,
                            "mutation_passed": False,
                            "property_passed": False,
                        }
                    )

                    failure = (
                        f"Regression tests failed.\n"
                        f"Exit code: "
                        f"{test_result['exit_code']}\n"
                        f"STDOUT:\n"
                        f"{test_result['stdout']}\n"
                        f"STDERR:\n"
                        f"{test_result['stderr']}"
                    )

                    continue

                repaired = True

                attempts.append(
                    {
                        "attempt": attempt_number,
                        "runtime_passed": True,
                        "tests_passed": True,
                        "mutation_passed": None,
                        "property_passed": None,
                    }
                )

                break

            if not repaired:
                result = {
                    "success": False,
                    "verified": False,
                    "behavior_verified": False,
                    "mutation_verified": False,
                    "property_verified": False,
                    "property_available": False,
                    "code": current_code,
                    "fixed_code": current_code,
                    "repaired_code": current_code,
                    "attempts": attempts,
                    "reason": (
                        "No repair candidate passed the "
                        "initial regression tests."
                    ),
                    "tests": tests,
                    "mutation": None,
                    "properties": None,
                    "strengthening": None,
                }

                self._record_experience(problem, result)
                return result

        # ---------------------------------------------------------
        # 4. Candidate now passes initial tests.
        #    Strengthen those tests against THIS candidate.
        # ---------------------------------------------------------
        strengthening = self.strengthen_tests(
            code=current_code,
            tests=tests,
        )

        if not strengthening["success"]:
            result = {
                "success": False,
                "verified": False,
                "behavior_verified": True,
                "mutation_verified": False,
                "property_verified": False,
                "property_available": False,
                "code": current_code,
                "fixed_code": current_code,
                "repaired_code": current_code,
                "attempts": attempts,
                "reason": (
                    "Candidate passes initial regression tests, "
                    "but the test suite could not be strengthened "
                    "to the required mutation threshold."
                ),
                "tests": strengthening["tests"],
                "mutation": strengthening["mutation"],
                "properties": None,
                "strengthening": strengthening,
            }

            result["strategy"] = strategy_decision.applied
            result["requested_strategy"] = strategy_decision.requested
            result["strategy_fallback"] = strategy_decision.fallback
            result["strategy_reason"] = strategy_decision.reason

            self._record_experience(problem, result)
            return result

        tests = strengthening["tests"]

        # ---------------------------------------------------------
        # 5. Final unified acceptance check.
        # ---------------------------------------------------------
        acceptance = self._acceptance_check(
            code=current_code,
            problem=problem,
            tests=tests,
        )

        mutation = acceptance["mutation"]
        properties = acceptance["properties"]

        if attempts:
            attempts[-1]["mutation_passed"] = (
                acceptance["mutation_passed"]
            )

            attempts[-1]["mutation_score"] = (
                mutation["score"]
                if mutation
                else None
            )

            attempts[-1]["property_passed"] = (
                acceptance["property_passed"]
            )

            attempts[-1]["property_available"] = (
                acceptance["property_available"]
            )

        if acceptance["accepted"]:
            result = {
                "success": True,
                "verified": True,
                "behavior_verified": True,
                "mutation_verified": True,
                "property_verified": (
                    acceptance["property_passed"]
                ),
                "property_available": (
                    acceptance["property_available"]
                ),
                "code": current_code,
                "fixed_code": current_code,
                "repaired_code": current_code,
                "attempts": attempts,
                "reason": (
                    "Repair passed regression tests, "
                    "mutation testing, and all applicable "
                    "property checks."
                ),
                "tests": tests,
                "mutation": mutation,
                "properties": properties,
                "strengthening": strengthening,
            }

            result["strategy"] = strategy_decision.applied
            result["requested_strategy"] = strategy_decision.requested
            result["strategy_fallback"] = strategy_decision.fallback
            result["strategy_reason"] = strategy_decision.reason

            self._record_experience(problem, result)
            return result

        result = {
            "success": False,
            "verified": False,
            "behavior_verified": (
                acceptance["tests_passed"]
            ),
            "mutation_verified": (
                acceptance["mutation_passed"]
            ),
            "property_verified": (
                acceptance["property_passed"]
            ),
            "property_available": (
                acceptance["property_available"]
            ),
            "code": current_code,
            "fixed_code": current_code,
            "repaired_code": current_code,
            "attempts": attempts,
            "reason": (
                "Candidate failed one or more final "
                "verification gates.\n"
                f"{acceptance['failure']}"
            ),
            "tests": tests,
            "mutation": mutation,
            "properties": properties,
            "strengthening": strengthening,
        }

        result["strategy"] = strategy_decision.applied
        result["requested_strategy"] = strategy_decision.requested
        result["strategy_fallback"] = strategy_decision.fallback
        result["strategy_reason"] = strategy_decision.reason

        self._record_experience(problem, result)
        return result
