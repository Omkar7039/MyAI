import ast
import re


class TestGenerator:
    MAX_GENERATION_ATTEMPTS = 3

    def __init__(self, model):
        self.model = model

    def generate_python_tests(self, code: str, problem: str):
        intended_operation = self.detect_operation(problem)

        for _ in range(self.MAX_GENERATION_ATTEMPTS):
            operation_rule = ""

            if intended_operation == "add":
                operation_rule = (
                    "The required operation is ADDITION. "
                    "For example, add(10, -2) must expect 8."
                )
            elif intended_operation == "subtract":
                operation_rule = (
                    "The required operation is SUBTRACTION. "
                    "For example, subtract(10, -2) must expect 12."
                )
            elif intended_operation == "multiply":
                operation_rule = (
                    "The required operation is MULTIPLICATION. "
                    "For example, multiply(10, -2) must expect -20."
                )
            elif intended_operation == "divide":
                operation_rule = (
                    "The required operation is DIVISION. "
                    "Use non-zero divisors for normal division tests."
                )

            prompt = (
                "You are MyAI's independent regression-test generator.\n\n"
                "Generate executable Python regression tests from the "
                "USER REQUIREMENT.\n\n"
                "CRITICAL RULES:\n"
                "1. Never copy or redefine any source function or class.\n"
                "2. Never derive expected values from the current implementation.\n"
                "3. Expected values must come from the USER REQUIREMENT.\n"
                "4. Do not reproduce the implementation logic inside tests.\n"
                "5. Use plain Python assert statements.\n"
                "6. Do not use pytest or external packages.\n"
                "7. Test normal cases and useful edge cases.\n"
                "8. Return ONLY one Python code block containing test statements.\n\n"
                f"USER REQUIREMENT:\n{problem}\n\n"
                f"INTENDED OPERATION:\n{intended_operation or 'unknown'}\n"
                f"{operation_rule}\n\n"
                f"SOURCE API:\n```python\n{self.extract_public_api(code)}\n```\n"
            )

            response = self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=768,
            )

            tests = self.extract_tests(response)

            if not tests:
                continue

            if not self.validate_tests(tests):
                continue

            if not self.semantic_sanity_check(
                tests,
                problem,
            ):
                continue

            return tests

        return None

    def detect_operation(self, problem: str):
        text = problem.lower()

        # Order matters: check explicit phrases before shorter words.
        if (
            "addition" in text
            or "add two" in text
            or "add numbers" in text
            or "adds two" in text
            or "sum" in text
        ):
            return "add"

        if (
            "subtraction" in text
            or "subtract" in text
            or "subtracts two" in text
            or "difference" in text
        ):
            return "subtract"

        if (
            "multiplication" in text
            or "multiply" in text
            or "multiplies" in text
            or "product" in text
        ):
            return "multiply"

        if (
            "division" in text
            or "divide" in text
            or "divides" in text
            or "quotient" in text
        ):
            return "divide"

        return None

    def extract_public_api(self, code: str):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code

        api = []

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                arguments = [
                    arg.arg
                    for arg in node.args.args
                ]

                api.append(
                    f"def {node.name}({', '.join(arguments)}): ..."
                )

            elif isinstance(node, ast.AsyncFunctionDef):
                arguments = [
                    arg.arg
                    for arg in node.args.args
                ]

                api.append(
                    f"async def {node.name}"
                    f"({', '.join(arguments)}): ..."
                )

            elif isinstance(node, ast.ClassDef):
                api.append(f"class {node.name}: ...")

        return "\n".join(api)

    def extract_tests(self, response: str):
        match = re.search(
            r"```python\s*(.*?)```",
            response,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return match.group(1).strip()

        match = re.search(
            r"```\s*(.*?)```",
            response,
            re.DOTALL,
        )

        if match:
            return match.group(1).strip()

        return None

    def validate_tests(self, test_code: str):
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return False

        if not tree.body:
            return False

        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                    ast.Import,
                    ast.ImportFrom,
                ),
            ):
                return False

        assertions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        ]

        return bool(assertions)

    def semantic_sanity_check(
        self,
        test_code: str,
        problem: str,
    ):
        operation = self.detect_operation(problem)

        if operation is None:
            return True

        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return False

        assertions_found = False

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue

            assertions_found = True

            comparison = node.test

            if not isinstance(comparison, ast.Compare):
                continue

            if len(comparison.ops) != 1:
                continue

            if not isinstance(comparison.ops[0], ast.Eq):
                continue

            if len(comparison.comparators) != 1:
                continue

            call = comparison.left
            expected = comparison.comparators[0]

            if not isinstance(call, ast.Call):
                continue

            if len(call.args) != 2:
                continue

            left = self._numeric_constant(call.args[0])
            right = self._numeric_constant(call.args[1])
            expected_value = self._numeric_constant(expected)

            if (
                left is None
                or right is None
                or expected_value is None
            ):
                continue

            try:
                if operation == "add":
                    correct = left + right

                elif operation == "subtract":
                    correct = left - right

                elif operation == "multiply":
                    correct = left * right

                elif operation == "divide":
                    if right == 0:
                        continue

                    correct = left / right

                else:
                    continue

            except Exception:
                continue

            if expected_value != correct:
                return False

        return assertions_found

    def _numeric_constant(self, node):
        if isinstance(node, ast.Constant):
            value = node.value

            if isinstance(
                value,
                (int, float),
            ) and not isinstance(
                value,
                bool,
            ):
                return value

        return None

    def build_test_program(
        self,
        source_code: str,
        test_code: str,
    ):
        if not test_code:
            return None

        return (
            source_code.rstrip()
            + "\n\n"
            + "# ===== MYAI GENERATED REGRESSION TESTS =====\n"
            + test_code.rstrip()
            + "\n"
            + "print('__MYAI_TESTS_PASSED__')\n"
        )
