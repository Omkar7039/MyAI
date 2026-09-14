import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FlowStep:
    caller: str
    callee: str


class MultiFileAnalyzer:
    INTERNAL_ROOTS = (
        "agents/",
        "core/",
        "project/",
        "router/",
        "tools/",
        "verification/",
        "models/",
    )

    FLOW_PRIORITY = {
        "handle": 100,
        "build_request": 95,
        "route": 90,
        "analyze": 85,
        "repair_and_verify": 85,
        "run_tests": 75,
        "strengthen_tests": 70,
        "mutation_check": 70,
        "run_properties": 70,
        "verify": 60,
    }

    PREPROCESSING_METHODS = {
        "extract_code",
        "detect_language",
        "_max_tokens_for",
        "_choose_model",
    }

    DATA_METHODS = {
        "Request",
    }

    DEPENDENCY_MAP = {
        (
            "core/orchestrator.py",
            "Orchestrator",
            "router",
        ): "router/intent_router.py:IntentRouter",

        (
            "core/orchestrator.py",
            "Orchestrator",
            "difficulty_router",
        ): "router/difficulty_router.py:DifficultyRouter",

        (
            "core/orchestrator.py",
            "Orchestrator",
            "model_router",
        ): "router/model_router.py:ModelRouter",

        (
            "core/orchestrator.py",
            "Orchestrator",
            "debug_agent",
        ): "agents/debugging.py:DebugAgent",

        (
            "agents/debugging.py",
            "DebugAgent",
            "analyzer",
        ): "tools/code_analyzer.py:CodeAnalyzer",

        (
            "agents/debugging.py",
            "DebugAgent",
            "runner_manager",
        ): "tools/runner_manager.py:RunnerManager",

        (
            "agents/debugging.py",
            "DebugAgent",
            "repair_agent",
        ): "agents/repair.py:RepairAgent",

        (
            "agents/repair.py",
            "RepairAgent",
            "runner_manager",
        ): "tools/runner_manager.py:RunnerManager",

        (
            "agents/repair.py",
            "RepairAgent",
            "test_generator",
        ): "verification/test_generator.py:TestGenerator",

        (
            "agents/repair.py",
            "RepairAgent",
            "mutation_engine",
        ): "verification/mutation_engine.py:MutationEngine",

        (
            "agents/repair.py",
            "RepairAgent",
            "test_strengthener",
        ): "verification/test_strengthener.py:TestStrengthener",

        (
            "agents/repair.py",
            "RepairAgent",
            "property_engine",
        ): "verification/property_engine.py:PropertyEngine",
    }

    def analyze_flow(
        self,
        context,
        start_symbols=None,
        goal_symbols=None,
        max_depth=8,
    ):
        graph = self._build_graph(context)

        if start_symbols is None:
            start_symbols = self._default_entrypoints(context)

        if goal_symbols is None:
            goal_symbols = self._default_goals(context)

        traces = []

        for start in start_symbols:
            trace = self._find_goal_path(
                graph=graph,
                current=start,
                goals=set(goal_symbols),
                visited=set(),
                depth=0,
                max_depth=max_depth,
            )

            if trace:
                traces.append(trace)
            else:
                # Fall back to a normal useful application path.
                fallback = self._walk(
                    graph,
                    start,
                    set(),
                    0,
                    max_depth,
                )

                if fallback:
                    traces.append(fallback)

        return self._dedupe_traces(traces)

    def _default_goals(self, context):
        wanted = {
            "agents/debugging.py:DebugAgent.analyze",
            "agents/repair.py:RepairAgent.repair_and_verify",
        }

        found = []

        for file_index in context.code_index.files:
            for symbol in file_index.symbols:
                parent = getattr(symbol, "parent", None)
                name = getattr(symbol, "name", "")

                qualified = (
                    f"{parent}.{name}"
                    if parent
                    else name
                )

                identifier = f"{symbol.file}:{qualified}"

                if identifier in wanted:
                    found.append(identifier)

        return found

    def _find_goal_path(
        self,
        graph,
        current,
        goals,
        visited,
        depth,
        max_depth,
    ):
        if current in goals:
            return [current]

        if depth >= max_depth:
            return None

        if current in visited:
            return None

        visited = set(visited)
        visited.add(current)

        candidates = []

        for target in graph.get(current, []):
            if target in visited:
                continue

            if not self._is_useful_target(target):
                continue

            candidates.append(target)

        candidates.sort(
            key=lambda value: (
                0 if value in goals else 1,
                -self._target_priority(value),
            )
        )

        for candidate in candidates:
            result = self._find_goal_path(
                graph=graph,
                current=candidate,
                goals=goals,
                visited=visited,
                depth=depth + 1,
                max_depth=max_depth,
            )

            if result:
                return [current] + result

        return None

    def analyze_branches(
        self,
        context,
        start_symbol,
        max_depth=5,
        max_children=5,
    ):
        """
        Return a bounded branch tree with verified AST conditions.
        """

        graph = self._build_graph(context)

        return self._build_branch_node(
            context=context,
            graph=graph,
            current=start_symbol,
            visited=set(),
            depth=0,
            max_depth=max_depth,
            max_children=max_children,
        )

    def _build_branch_node(
        self,
        context,
        graph,
        current,
        visited,
        depth,
        max_depth,
        max_children,
    ):
        node = {
            "symbol": current,
            "internal": current.startswith(self.INTERNAL_ROOTS),
            "condition": None,
            "children": [],
        }

        if depth >= max_depth or current in visited:
            return node

        visited = set(visited)
        visited.add(current)

        conditions = self._conditions_for_caller(
            context,
            current,
        )

        candidates = []

        for target in graph.get(current, []):
            if target in visited:
                continue

            if not self._is_useful_target(target):
                continue

            candidates.append(target)

        candidates.sort(
            key=self._target_priority,
            reverse=True,
        )

        for target in candidates[:max_children]:
            child = self._build_branch_node(
                context=context,
                graph=graph,
                current=target,
                visited=visited,
                depth=depth + 1,
                max_depth=max_depth,
                max_children=max_children,
            )

            target_conditions = conditions.get(target)

            if target_conditions:
                child["condition"] = target_conditions

            node["children"].append(child)

        return node

    def _conditions_for_caller(self, context, caller):
        """
        Return condition alternatives for calls inside one caller.

        Representation:
            target -> [
                ["outer_condition", "nested_condition"],
                ["another_condition"],
            ]

        Each inner list is one AND path.
        Multiple paths are OR alternatives.
        """
        if ":" not in caller:
            return {}

        file_path, qualified = caller.split(":", 1)

        if "." in qualified:
            parent, method_name = qualified.rsplit(".", 1)
        else:
            parent = None
            method_name = qualified

        source = self._read_project_source(
            context,
            file_path,
        )

        if source is None:
            return {}

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {}

        target_node = self._find_method_node(
            tree,
            parent,
            method_name,
        )

        if target_node is None:
            return {}

        condition_map = {}

        def record_call(call_node, conditions):
            try:
                expression = ast.unparse(call_node.func)
            except Exception:
                return

            resolved = self._resolve_condition_target(
                context,
                caller,
                expression,
            )

            if not resolved:
                return

            paths = condition_map.setdefault(
                resolved,
                [],
            )

            condition_path = list(conditions)

            # Empty path means unconditional call.
            if not condition_path:
                condition_path = ["ALWAYS"]

            if condition_path not in paths:
                paths.append(condition_path)

        def walk(node, conditions):
            if isinstance(node, ast.If):
                try:
                    condition = ast.unparse(node.test)
                except Exception:
                    condition = "<unavailable condition>"

                body_conditions = list(conditions)
                body_conditions.append(condition)

                for child in node.body:
                    walk(child, body_conditions)

                if node.orelse:
                    else_conditions = list(conditions)
                    else_conditions.append(
                        f"NOT ({condition})"
                    )

                    for child in node.orelse:
                        walk(child, else_conditions)

                return

            if isinstance(node, ast.Call):
                record_call(node, conditions)

            for child in ast.iter_child_nodes(node):
                walk(child, conditions)

        for statement in target_node.body:
            walk(statement, [])

        return condition_map

    def _find_method_node(self, tree, parent, method_name):
        for node in ast.walk(tree):
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if node.name != method_name:
                continue

            # Search enclosing class definitions.
            for class_node in ast.walk(tree):
                if not isinstance(class_node, ast.ClassDef):
                    continue

                if class_node.name != parent:
                    continue

                for child in class_node.body:
                    if (
                        isinstance(
                            child,
                            (
                                ast.FunctionDef,
                                ast.AsyncFunctionDef,
                            ),
                        )
                        and child.name == method_name
                    ):
                        return child

        return None

    def _read_project_source(self, context, file_path):
        root = getattr(context, "root", None)

        if root is None:
            return None

        try:
            root = Path(root)
            return (root / file_path).read_text(
                encoding="utf-8",
            )
        except (OSError, UnicodeDecodeError):
            return None

    def _resolve_condition_target(
        self,
        context,
        caller,
        expression,
    ):
        """
        Resolve a raw AST call such as:
            self.debug_agent.analyze
        into:
            agents/debugging.py:DebugAgent.analyze
        """

        targets = self._resolve_dependency_calls(
            context,
            caller,
            [expression],
        )

        if targets:
            return targets[0]

        if expression.startswith("self."):
            method = expression[len("self."):]

            if "." not in method:
                resolved = self._resolve_same_class_method(
                    context,
                    caller,
                    method,
                )

                if resolved:
                    return resolved

        return None

    def _resolve_same_class_method(
        self,
        context,
        caller,
        method,
    ):
        if ":" not in caller:
            return None

        file_path, qualified = caller.split(":", 1)

        parent = (
            qualified.rsplit(".", 1)[0]
            if "." in qualified
            else None
        )

        if not parent:
            return None

        for file_index in context.code_index.files:
            for symbol in file_index.symbols:
                if symbol.file != file_path:
                    continue

                if getattr(symbol, "parent", None) != parent:
                    continue

                if symbol.name != method:
                    continue

                return (
                    f"{symbol.file}:"
                    f"{parent}.{symbol.name}"
                )

        return None

    def _build_graph(self, context):
        graph = {}

        # Raw AST calls.
        for edge in context.call_graph.edges:
            caller = getattr(edge, "caller", "")
            callee = getattr(edge, "callee", "")

            if caller and callee:
                graph.setdefault(caller, []).append(callee)

        # Resolver results.
        resolutions = getattr(context, "resolutions", {})

        if isinstance(resolutions, dict):
            for caller, targets in resolutions.items():
                graph.setdefault(caller, [])

                for target in targets:
                    if target:
                        graph[caller].append(target)

        # Resolve known self.attribute dependencies.
        for caller in list(graph):
            graph[caller].extend(
                self._resolve_dependency_calls(
                    context,
                    caller,
                    graph[caller],
                )
            )

        for caller in list(graph):
            graph[caller] = self._dedupe(graph[caller])

        return graph

    def _resolve_dependency_calls(
        self,
        context,
        caller,
        calls,
    ):
        results = []

        if ":" not in caller:
            return results

        caller_file, caller_symbol = caller.split(":", 1)

        if "." not in caller_symbol:
            return results

        parent = caller_symbol.rsplit(".", 1)[0]

        for call in calls:
            parts = call.split(".")

            if len(parts) != 3:
                continue

            first, dependency, method = parts

            if first != "self":
                continue

            target_class = self.DEPENDENCY_MAP.get(
                (
                    caller_file,
                    parent,
                    dependency,
                )
            )

            if not target_class:
                continue

            results.append(
                f"{target_class}.{method}"
            )

        # self.method(...)
        for call in calls:
            if not call.startswith("self."):
                continue

            method = call[len("self."):]

            if "." in method:
                continue

            resolved = self._resolve_same_class_method(
                context,
                caller_file,
                parent,
                method,
            )

            if resolved:
                results.append(resolved)

        return results

    def _resolve_same_class_method(
        self,
        context,
        caller_file,
        parent,
        method,
    ):
        for file_index in context.code_index.files:
            for symbol in file_index.symbols:
                if symbol.file != caller_file:
                    continue

                if getattr(symbol, "parent", None) != parent:
                    continue

                if symbol.name != method:
                    continue

                return (
                    f"{symbol.file}:"
                    f"{parent}.{symbol.name}"
                )

        return None

    def _walk(
        self,
        graph,
        current,
        visited,
        depth,
        max_depth,
    ):
        if depth >= max_depth:
            return [current]

        if current in visited:
            return [current]

        visited = set(visited)
        visited.add(current)

        candidates = []

        for target in graph.get(current, []):
            if target in visited:
                continue

            if not self._is_useful_target(target):
                continue

            candidates.append(target)

        if not candidates:
            return [current]

        candidates.sort(
            key=self._target_priority,
            reverse=True,
        )

        # Prefer application-flow calls over preprocessing.
        best = candidates[0]

        child = self._walk(
            graph,
            best,
            visited,
            depth + 1,
            max_depth,
        )

        return [current] + child

    def _is_useful_target(self, value):
        if not value:
            return False

        if not value.startswith(self.INTERNAL_ROOTS):
            return False

        method = self._method_name(value)

        # Keep preprocessing only when there is no better application call.
        # The ranking function will strongly demote it.
        return method not in self.DATA_METHODS

    def _target_priority(self, value):
        method = self._method_name(value)

        score = 0

        if value.startswith(self.INTERNAL_ROOTS):
            score += 20

        score += self.FLOW_PRIORITY.get(
            method,
            10,
        )

        if method in self.PREPROCESSING_METHODS:
            score -= 60

        if method in self.DATA_METHODS:
            score -= 80

        if method.startswith("_"):
            score -= 20

        return score

    def _method_name(self, identifier):
        value = identifier

        if ":" in value:
            value = value.split(":", 1)[1]

        if "." in value:
            return value.rsplit(".", 1)[1]

        return value

    def format_condition(self, condition):
        """
        Convert condition data into a readable boolean expression.

        Input may be:
            None
            ["ALWAYS"]
            ["condition_a", "condition_b"]
            [
                ["condition_a"],
                ["condition_b", "condition_c"],
            ]
        """
        if not condition:
            return "ALWAYS"

        # One AND path.
        if all(isinstance(item, str) for item in condition):
            if condition == ["ALWAYS"]:
                return "ALWAYS"

            return " AND ".join(condition)

        # Multiple alternative paths = OR.
        paths = []

        for path in condition:
            if not path:
                continue

            if path == ["ALWAYS"]:
                paths.append("ALWAYS")
            else:
                paths.append(
                    " AND ".join(path)
                )

        if not paths:
            return "ALWAYS"

        if len(paths) == 1:
            return paths[0]

        return " OR ".join(
            f"({item})"
            for item in paths
        )

    def _default_entrypoints(self, context):
        wanted = {
            "core/orchestrator.py:Orchestrator.handle",
            "core/orchestrator.py:Orchestrator.build_request",
            "agents/debugging.py:DebugAgent.analyze",
            "agents/repair.py:RepairAgent.repair_and_verify",
        }

        found = []

        for file_index in context.code_index.files:
            for symbol in file_index.symbols:
                parent = getattr(symbol, "parent", None)
                name = getattr(symbol, "name", "")

                qualified = (
                    f"{parent}.{name}"
                    if parent
                    else name
                )

                identifier = f"{symbol.file}:{qualified}"

                if identifier in wanted:
                    found.append(identifier)

        return found

    def _dedupe(self, values):
        result = []
        seen = set()

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            result.append(value)

        return result

    def _dedupe_traces(self, traces):
        result = []
        seen = set()

        for trace in traces:
            key = tuple(trace)

            if key in seen:
                continue

            seen.add(key)
            result.append(trace)

        return result
