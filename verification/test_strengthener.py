import ast
import re


class TestStrengthener:
    MAX_ATTEMPTS = 5

    def __init__(self, model, mutation_engine):
        self.model = model
        self.mutation_engine = mutation_engine

    def strengthen(
        self,
        source_code: str,
        tests: str,
    ):
        current_tests = tests
        history = []

        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            mutation_result = (
                self.mutation_engine.evaluate_test_strength(
                    source_code=source_code,
                    tests=current_tests,
                )
            )

            history.append(
                {
                    "attempt": attempt,
                    "score": mutation_result["score"],
                    "caught": mutation_result[
                        "mutations_caught"
                    ],
                    "survived": mutation_result[
                        "mutations_survived"
                    ],
                }
            )

            if mutation_result["strong"]:
                return {
                    "success": True,
                    "tests": current_tests,
                    "mutation": mutation_result,
                    "history": history,
                    "reason": (
                        "Regression suite reached the required "
                        "mutation strength."
                    ),
                }

            survivors = [
                item
                for item in mutation_result["results"]
                if item["status"] == "SURVIVED"
            ]

            if not survivors:
                return {
                    "success": False,
                    "tests": current_tests,
                    "mutation": mutation_result,
                    "history": history,
                    "reason": (
                        "No surviving mutations were available "
                        "for targeted strengthening."
                    ),
                }

            strengthened = False

            for survivor in survivors:
                new_test = self.generate_targeted_test(
                    source_code=source_code,
                    current_tests=current_tests,
                    survivor=survivor,
                )

                if not new_test:
                    continue

                if not self.validate_test(new_test):
                    continue

                if self._duplicate_test(
                    current_tests,
                    new_test,
                ):
                    continue

                current_tests += (
                    "\n" + new_test
                )

                strengthened = True
                break

            if not strengthened:
                return {
                    "success": False,
                    "tests": current_tests,
                    "mutation": mutation_result,
                    "history": history,
                    "reason": (
                        "Could not generate a new valid "
                        "targeted test for any survivor."
                    ),
                }

        final_mutation = (
            self.mutation_engine.evaluate_test_strength(
                source_code=source_code,
                tests=current_tests,
            )
        )

        return {
            "success": final_mutation["strong"],
            "tests": current_tests,
            "mutation": final_mutation,
            "history": history,
            "reason": (
                "Test strengthening completed."
                if final_mutation["strong"]
                else
                "Test strengthening limit reached."
            ),
        }

    def generate_targeted_test(
        self,
        source_code: str,
        current_tests: str,
        survivor: dict,
    ):
        description = survivor["description"]

        guidance = self._mutation_guidance(
            description
        )

        prompt = (
            "You are MyAI's targeted regression-test generator.\n\n"
            "A specific mutation survived the current tests.\n"
            "Generate ONE additional Python assert statement that "
            "kills this exact mutation while checking intended behavior.\n\n"
            "RULES:\n"
            "1. Return exactly ONE assert statement.\n"
            "2. Do not define functions or classes.\n"
            "3. Do not import anything.\n"
            "4. Do not modify existing tests.\n"
            "5. Do not copy implementation code.\n"
            "6. Expected values must represent intended behavior.\n"
            "7. Prefer the smallest boundary or edge case that "
            "distinguishes the original from the mutation.\n\n"
            f"MUTATION:\n{description}\n\n"
            f"TARGETING GUIDANCE:\n{guidance}\n\n"
            f"SOURCE:\n```python\n{source_code}\n```\n\n"
            f"EXISTING TESTS:\n```python\n{current_tests}\n```\n"
        )

        response = self.model.ask(
            [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=256,
        )

        return self.extract_assert(response)

    def _mutation_guidance(self, description: str):
        text = description.lower()

        if "greater" in text:
            return (
                "Use a boundary where the compared values are equal. "
                "For example, if the original checks a > b, exercise "
                "a == b."
            )

        if "less" in text:
            return (
                "Use equality or the exact threshold boundary to "
                "distinguish < from <= or other comparison variants."
            )

        if "not equal" in text or "equal" in text:
            return (
                "Use equal and unequal values around the comparison "
                "boundary."
            )

        if "and -> or" in text:
            return (
                "Make one condition true and the other false so "
                "AND and OR produce different results."
            )

        if "or -> and" in text:
            return (
                "Make exactly one operand true so OR and AND "
                "produce different results."
            )

        if "return expression" in text:
            return (
                "Choose an input where the function's returned value "
                "is observable and is definitely not None."
            )

        if "integer" in text:
            return (
                "Exercise the exact boundary represented by the "
                "constant and a nearby value."
            )

        if "float" in text:
            return (
                "Exercise a value where changing the constant by "
                "1.0 changes the expected result."
            )

        if "add" in text:
            return (
                "Choose non-zero operands where addition and the "
                "mutated arithmetic operation produce different results."
            )

        if "subtract" in text:
            return (
                "Choose non-zero operands where subtraction and the "
                "mutated operation produce different results."
            )

        return (
            "Choose a deterministic edge case that makes the "
            "original and mutated behavior differ."
        )

    def extract_assert(self, response: str):
        match = re.search(
            r"```python\s*(.*?)```",
            response,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            text = match.group(1).strip()
        else:
            text = response.strip()

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        assertions = [
            line
            for line in lines
            if line.startswith("assert ")
        ]

        if len(assertions) != 1:
            return None

        return assertions[0]

    def validate_test(self, test_code: str):
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return False

        if len(tree.body) != 1:
            return False

        node = tree.body[0]

        if not isinstance(node, ast.Assert):
            return False

        return True

    def _duplicate_test(
        self,
        tests: str,
        new_test: str,
    ):
        existing = {
            line.strip()
            for line in tests.splitlines()
            if line.strip()
        }

        return new_test.strip() in existing
