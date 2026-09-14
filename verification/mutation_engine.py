import ast
import copy
from dataclasses import dataclass


@dataclass
class Mutation:
    mutation_id: int
    description: str
    source_code: str


class MutationEngine:
    def __init__(self, runner_manager):
        self.runner_manager = runner_manager

    def generate_mutations(self, source_code: str):
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        mutations = []

        for node in ast.walk(tree):
            for description, mutator in self._mutation_rules(node):
                mutated_tree = copy.deepcopy(tree)

                target = self._find_matching_node(
                    mutated_tree,
                    node,
                )

                if target is None:
                    continue

                changed = mutator(target)

                if not changed:
                    continue

                ast.fix_missing_locations(mutated_tree)

                try:
                    mutated_source = ast.unparse(mutated_tree)
                except Exception:
                    continue

                mutations.append(
                    Mutation(
                        mutation_id=len(mutations) + 1,
                        description=description,
                        source_code=mutated_source,
                    )
                )

        return self._deduplicate(mutations)

    def _mutation_rules(self, node):
        rules = []

        # ---------------------------------------------------------
        # Arithmetic operators
        # ---------------------------------------------------------
        if isinstance(node, ast.Add):
            rules.append(
                (
                    "Add (+) -> Subtract (-)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Sub(),
                    ),
                )
            )

        elif isinstance(node, ast.Sub):
            rules.append(
                (
                    "Subtract (-) -> Add (+)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Add(),
                    ),
                )
            )

        elif isinstance(node, ast.Mult):
            rules.append(
                (
                    "Multiply (*) -> Divide (/)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Div(),
                    ),
                )
            )

        elif isinstance(node, ast.Div):
            rules.append(
                (
                    "Divide (/) -> Multiply (*)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Mult(),
                    ),
                )
            )

        # ---------------------------------------------------------
        # Comparisons
        # ---------------------------------------------------------
        elif isinstance(node, ast.Eq):
            rules.append(
                (
                    "Equal (==) -> Not equal (!=)",
                    lambda target: self._replace_operator(
                        target,
                        ast.NotEq(),
                    ),
                )
            )

        elif isinstance(node, ast.NotEq):
            rules.append(
                (
                    "Not equal (!=) -> Equal (==)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Eq(),
                    ),
                )
            )

        elif isinstance(node, ast.Lt):
            rules.append(
                (
                    "Less (<) -> Less/equal (<=)",
                    lambda target: self._replace_operator(
                        target,
                        ast.LtE(),
                    ),
                )
            )

            rules.append(
                (
                    "Less (<) -> Greater/equal (>=)",
                    lambda target: self._replace_operator(
                        target,
                        ast.GtE(),
                    ),
                )
            )

        elif isinstance(node, ast.LtE):
            rules.append(
                (
                    "Less/equal (<=) -> Less (<)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Lt(),
                    ),
                )
            )

        elif isinstance(node, ast.Gt):
            rules.append(
                (
                    "Greater (>) -> Greater/equal (>=)",
                    lambda target: self._replace_operator(
                        target,
                        ast.GtE(),
                    ),
                )
            )

            rules.append(
                (
                    "Greater (>) -> Less/equal (<=)",
                    lambda target: self._replace_operator(
                        target,
                        ast.LtE(),
                    ),
                )
            )

        elif isinstance(node, ast.GtE):
            rules.append(
                (
                    "Greater/equal (>=) -> Greater (>)",
                    lambda target: self._replace_operator(
                        target,
                        ast.Gt(),
                    ),
                )
            )

        # ---------------------------------------------------------
        # Boolean operators
        # ---------------------------------------------------------
        elif isinstance(node, ast.And):
            rules.append(
                (
                    "AND -> OR",
                    lambda target: self._replace_operator(
                        target,
                        ast.Or(),
                    ),
                )
            )

        elif isinstance(node, ast.Or):
            rules.append(
                (
                    "OR -> AND",
                    lambda target: self._replace_operator(
                        target,
                        ast.And(),
                    ),
                )
            )

        elif isinstance(node, ast.Not):
            rules.append(
                (
                    "NOT condition -> condition",
                    self._remove_not,
                )
            )

        # ---------------------------------------------------------
        # Boolean constants
        # ---------------------------------------------------------
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                rules.append(
                    (
                        f"Boolean {node.value} -> {not node.value}",
                        lambda target: self._replace_constant(
                            target,
                            not target.value,
                        ),
                    )
                )

            # Numeric constants.
            elif (
                isinstance(node.value, int)
                and not isinstance(node.value, bool)
            ):
                rules.append(
                    (
                        f"Integer {node.value} -> {node.value + 1}",
                        lambda target: self._replace_constant(
                            target,
                            target.value + 1,
                        ),
                    )
                )

                rules.append(
                    (
                        f"Integer {node.value} -> {node.value - 1}",
                        lambda target: self._replace_constant(
                            target,
                            target.value - 1,
                        ),
                    )
                )

        # ---------------------------------------------------------
        # Return-value mutations
        # ---------------------------------------------------------
        elif isinstance(node, ast.Return):
            if node.value is not None:
                rules.append(
                    (
                        "Return expression -> None",
                        lambda target: self._replace_return_value(
                            target
                        ),
                    )
                )

        return rules

    def _replace_operator(
        self,
        target,
        new_operator,
    ):
        target.__class__ = new_operator.__class__

        for field in new_operator._fields:
            setattr(
                target,
                field,
                getattr(new_operator, field),
            )

        return True

    def _replace_constant(
        self,
        target,
        new_value,
    ):
        if not isinstance(target, ast.Constant):
            return False

        target.value = new_value
        return True

    def _replace_return_value(
        self,
        target,
    ):
        if not isinstance(target, ast.Return):
            return False

        target.value = ast.Constant(value=None)
        return True

    def _remove_not(
        self,
        target,
    ):
        if not isinstance(target, ast.Not):
            return False

        # Replace "not X" with X by copying the operand into
        # the current node's parent is not possible directly here.
        # Instead, mutate the Not node to a constant False.
        target.__class__ = ast.Constant
        target.value = False
        target.kind = None

        return True

    def _find_matching_node(
        self,
        tree,
        original_node,
    ):
        original_type = type(original_node)

        candidates = [
            node
            for node in ast.walk(tree)
            if type(node) is original_type
        ]

        for candidate in candidates:
            if (
                getattr(candidate, "lineno", None)
                == getattr(original_node, "lineno", None)
                and getattr(candidate, "col_offset", None)
                == getattr(original_node, "col_offset", None)
            ):
                return candidate

        return None

    def _deduplicate(
        self,
        mutations,
    ):
        seen = set()
        unique = []

        for mutation in mutations:
            if mutation.source_code in seen:
                continue

            seen.add(mutation.source_code)

            mutation.mutation_id = len(unique) + 1

            unique.append(mutation)

        return unique

    def evaluate_test_strength(
        self,
        source_code: str,
        tests: str,
    ):
        mutations = self.generate_mutations(
            source_code
        )

        if not mutations:
            return {
                "strong": False,
                "score": 0.0,
                "mutations_total": 0,
                "mutations_caught": 0,
                "mutations_survived": 0,
                "results": [],
                "reason": (
                    "No supported mutations could be generated."
                ),
            }

        results = []
        caught = 0

        for mutation in mutations:
            program = (
                mutation.source_code.rstrip()
                + "\n\n"
                + "# ===== MYAI MUTATION TESTS =====\n"
                + tests.rstrip()
                + "\n"
                + "print('__MUTATION_SURVIVED__')\n"
            )

            try:
                execution = self.runner_manager.run(
                    "python",
                    program,
                )
            except Exception as exc:
                execution = {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(exc),
                    "timed_out": False,
                }

            mutation_caught = not execution["success"]

            if mutation_caught:
                caught += 1

            results.append(
                {
                    "mutation_id": mutation.mutation_id,
                    "description": mutation.description,
                    "status": (
                        "CAUGHT"
                        if mutation_caught
                        else "SURVIVED"
                    ),
                    "exit_code": execution["exit_code"],
                    "stdout": execution["stdout"],
                    "stderr": execution["stderr"],
                }
            )

        total = len(mutations)
        survived = total - caught
        score = caught / total

        return {
            "strong": score >= 0.80,
            "score": score,
            "mutations_total": total,
            "mutations_caught": caught,
            "mutations_survived": survived,
            "results": results,
            "reason": (
                f"Caught {caught} of {total} generated mutations."
            ),
        }
