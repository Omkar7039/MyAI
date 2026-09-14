import ast
import re


class PropertyEngine:
    def __init__(self, runner_manager):
        self.runner_manager = runner_manager

    def infer_properties(
        self,
        source_code: str,
        problem: str,
    ):
        properties = []

        function_names = self._get_function_names(
            source_code
        )

        text = problem.lower()

        # Addition
        if (
            "add" in text
            or "addition" in text
        ):
            for name in function_names:
                if "add" in name.lower():
                    properties.extend(
                        [
                            f"assert {name}(2, 3) == 5",
                            f"assert {name}(3, 2) == 5",
                            f"assert {name}(-2, 2) == 0",
                            f"assert {name}(0, 0) == 0",
                        ]
                    )
                    break

        # Sorting
        if (
            "sort" in text
            or "sorting" in text
        ):
            for name in function_names:
                if "sort" in name.lower():
                    properties.extend(
                        [
                            (
                                f"_x = {name}([3, 1, 2]); "
                                f"assert _x == [1, 2, 3]"
                            ),
                            (
                                f"_x = {name}([]); "
                                f"assert _x == []"
                            ),
                        ]
                    )
                    break

        # Reverse
        if (
            "reverse" in text
            or "reversal" in text
        ):
            for name in function_names:
                if "reverse" in name.lower():
                    properties.extend(
                        [
                            (
                                f"_x = [1, 2, 3]; "
                                f"assert {name}({name}(_x)) == _x"
                            ),
                        ]
                    )
                    break

        return self._deduplicate(properties)

    def verify(
        self,
        source_code: str,
        problem: str,
    ):
        properties = self.infer_properties(
            source_code,
            problem,
        )

        if not properties:
            return {
                "available": False,
                "passed": False,
                "properties": [],
                "score": 0.0,
                "reason": (
                    "No deterministic properties could be inferred."
                ),
            }

        program = (
            source_code.rstrip()
            + "\n\n"
            + "# ===== MYAI PROPERTY CHECKS =====\n"
            + "\n".join(properties)
            + "\n"
            + "print('__MYAI_PROPERTIES_PASSED__')\n"
        )

        try:
            result = self.runner_manager.run(
                "python",
                program,
            )
        except Exception as exc:
            return {
                "available": True,
                "passed": False,
                "properties": properties,
                "score": 0.0,
                "reason": str(exc),
            }

        passed = result["success"]

        return {
            "available": True,
            "passed": passed,
            "properties": properties,
            "score": 1.0 if passed else 0.0,
            "reason": (
                "All inferred properties passed."
                if passed
                else
                "One or more inferred properties failed."
            ),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"],
        }

    def _get_function_names(self, source_code: str):
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        names = []

        for node in tree.body:
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                names.append(node.name)

        return names

    def _deduplicate(self, properties):
        seen = set()
        result = []

        for prop in properties:
            if prop in seen:
                continue

            seen.add(prop)
            result.append(prop)

        return result
