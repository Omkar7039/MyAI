from dataclasses import dataclass, field
from pathlib import Path
import ast


@dataclass
class Definition:
    name: str
    qualified_name: str
    file: str
    kind: str
    line: int
    parent: str | None = None


@dataclass
class ResolutionResult:
    caller: str
    expression: str
    resolved_to: list[str] = field(default_factory=list)


@dataclass
class InstanceBinding:
    owner: str
    attribute: str
    class_name: str


class SymbolResolver:
    IGNORED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
    }

    def __init__(self):
        self.definitions = []
        self.by_name = {}
        self.by_qualified_name = {}
        self.instance_bindings = {}

    def index_repository(self, root: str | Path):
        root_path = Path(root).expanduser().resolve()

        self.definitions.clear()
        self.by_name.clear()
        self.by_qualified_name.clear()
        self.instance_bindings.clear()

        for path in root_path.rglob("*.py"):
            if self._ignored(path, root_path):
                continue

            self._index_file(
                path,
                root_path,
            )

        return self

    def resolve_call(
        self,
        expression: str,
        caller_file: str | None = None,
        caller_class: str | None = None,
        caller_scope: str | None = None,
    ):
        expression = expression.strip()

        results = []

        # ---------------------------------------------------------
        # Direct function/class call:
        # foo(...)
        # Request(...)
        # LocalModel(...)
        # ---------------------------------------------------------
        if "." not in expression:
            candidates = self.by_name.get(
                expression,
                [],
            )

            for definition in candidates:
                results.append(
                    definition.qualified_name
                )

            return sorted(set(results))

        parts = expression.split(".")

        # ---------------------------------------------------------
        # self.attribute.method(...)
        # Resolve attribute type first.
        # ---------------------------------------------------------
        if (
            parts[0] == "self"
            and len(parts) >= 3
            and caller_class
        ):
            attribute = parts[1]
            method_name = parts[-1]

            class_name = self._resolve_instance_binding(
                caller_file=caller_file,
                caller_class=caller_class,
                attribute=attribute,
            )

            if class_name:
                candidates = self.by_name.get(
                    method_name,
                    [],
                )

                for definition in candidates:
                    if (
                        definition.kind
                        in {
                            "method",
                            "async_method",
                        }
                        and definition.parent == class_name
                    ):
                        results.append(
                            definition.qualified_name
                        )

                if results:
                    return sorted(set(results))

        # ---------------------------------------------------------
        # self.method(...)
        # ---------------------------------------------------------
        if (
            parts[0] == "self"
            and len(parts) == 2
            and caller_class
        ):
            method_name = parts[-1]

            candidates = self.by_name.get(
                method_name,
                [],
            )

            for definition in candidates:
                if (
                    definition.kind
                    in {
                        "method",
                        "async_method",
                    }
                    and definition.parent == caller_class
                ):
                    results.append(
                        definition.qualified_name
                    )

            return sorted(set(results))

        # ---------------------------------------------------------
        # class.method(...)
        # ---------------------------------------------------------
        if len(parts) >= 2:
            class_name = parts[-2]
            method_name = parts[-1]

            candidates = self.by_name.get(
                method_name,
                [],
            )

            for definition in candidates:
                if (
                    definition.kind
                    in {
                        "method",
                        "async_method",
                    }
                    and definition.parent == class_name
                ):
                    results.append(
                        definition.qualified_name
                    )

        return sorted(set(results))

    def resolve_graph(
        self,
        call_graph,
    ):
        results = []

        for edge in call_graph.edges:
            caller_file = edge.file

            caller_class = self._extract_class(
                edge.caller
            )

            caller_method = self._extract_method(
                edge.caller
            )

            resolved = self.resolve_call(
                expression=edge.callee,
                caller_file=caller_file,
                caller_class=caller_class,
                caller_scope=caller_method,
            )

            results.append(
                ResolutionResult(
                    caller=edge.caller,
                    expression=edge.callee,
                    resolved_to=resolved,
                )
            )

        return results

    def summary(
        self,
        results,
    ):
        resolved_count = sum(
            1
            for result in results
            if result.resolved_to
        )

        unresolved_count = (
            len(results)
            - resolved_count
        )

        lines = [
            f"Total calls: {len(results)}",
            f"Resolved calls: {resolved_count}",
            f"Unresolved calls: {unresolved_count}",
            "",
            "Resolution:",
        ]

        for result in results:
            if result.resolved_to:
                target = ", ".join(
                    result.resolved_to
                )
            else:
                target = "UNRESOLVED"

            lines.append(
                f"{result.caller}"
                f" -> {result.expression}"
                f" => {target}"
            )

        return "\n".join(lines)

    def _index_file(
        self,
        path: Path,
        root: Path,
    ):
        try:
            source = path.read_text(
                encoding="utf-8"
            )
        except (
            OSError,
            UnicodeDecodeError,
        ):
            return

        try:
            tree = ast.parse(
                source,
                filename=str(path),
            )
        except SyntaxError:
            return

        relative = str(
            path.relative_to(root)
        )

        visitor = _DefinitionVisitor(
            relative,
            self,
        )

        visitor.visit(tree)

    def _register(
        self,
        definition: Definition,
    ):
        self.definitions.append(
            definition
        )

        self.by_name.setdefault(
            definition.name,
            [],
        ).append(definition)

        self.by_qualified_name[
            definition.qualified_name
        ] = definition

    def _register_instance_binding(
        self,
        owner: str,
        attribute: str,
        class_name: str,
    ):
        key = (
            owner,
            attribute,
        )

        self.instance_bindings[key] = InstanceBinding(
            owner=owner,
            attribute=attribute,
            class_name=class_name,
        )

    def _resolve_instance_binding(
        self,
        caller_file: str | None,
        caller_class: str | None,
        attribute: str,
    ):
        if not caller_class:
            return None

        # First try current class.
        key = (
            f"{caller_file}:{caller_class}",
            attribute,
        )

        binding = self.instance_bindings.get(
            key
        )

        if binding:
            return binding.class_name

        # Also support class names without file prefix.
        for instance_key, value in self.instance_bindings.items():
            owner, attr = instance_key

            if (
                attr == attribute
                and owner.endswith(
                    f":{caller_class}"
                )
            ):
                return value.class_name

        return None

    def _extract_class(
        self,
        caller: str,
    ):
        parts = caller.split(":")

        if len(parts) != 2:
            return None

        scope = parts[1]
        scope_parts = scope.split(".")

        if len(scope_parts) >= 2:
            return scope_parts[-2]

        return None

    def _extract_method(
        self,
        caller: str,
    ):
        parts = caller.split(":")

        if len(parts) != 2:
            return None

        scope_parts = parts[1].split(".")

        if scope_parts:
            return scope_parts[-1]

        return None

    def _ignored(
        self,
        path,
        root,
    ):
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            return True

        return any(
            part in self.IGNORED_DIRECTORIES
            for part in parts
        )


class _DefinitionVisitor(ast.NodeVisitor):
    def __init__(
        self,
        file_path,
        resolver,
    ):
        self.file_path = file_path
        self.resolver = resolver
        self.scope = []

    def visit_ClassDef(
        self,
        node,
    ):
        qualified = (
            f"{self.file_path}:"
            + ".".join(
                self.scope + [node.name]
            )
        )

        self.resolver._register(
            Definition(
                name=node.name,
                qualified_name=qualified,
                file=self.file_path,
                kind="class",
                line=node.lineno,
                parent=(
                    self.scope[-1]
                    if self.scope
                    else None
                ),
            )
        )

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()

    def visit_FunctionDef(
        self,
        node,
    ):
        if self.scope:
            kind = "method"
        else:
            kind = "function"

        qualified = (
            f"{self.file_path}:"
            + ".".join(
                self.scope + [node.name]
            )
        )

        self.resolver._register(
            Definition(
                name=node.name,
                qualified_name=qualified,
                file=self.file_path,
                kind=kind,
                line=node.lineno,
                parent=(
                    self.scope[-1]
                    if self.scope
                    else None
                ),
            )
        )

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()

    def visit_AsyncFunctionDef(
        self,
        node,
    ):
        if self.scope:
            kind = "async_method"
        else:
            kind = "async_function"

        qualified = (
            f"{self.file_path}:"
            + ".".join(
                self.scope + [node.name]
            )
        )

        self.resolver._register(
            Definition(
                name=node.name,
                qualified_name=qualified,
                file=self.file_path,
                kind=kind,
                line=node.lineno,
                parent=(
                    self.scope[-1]
                    if self.scope
                    else None
                ),
            )
        )

        self.scope.append(node.name)

        self.generic_visit(node)

        self.scope.pop()

    def visit_Assign(
        self,
        node,
    ):
        self._record_instance_bindings(
            node
        )

        self.generic_visit(node)

    def visit_AnnAssign(
        self,
        node,
    ):
        self._record_instance_bindings(
            node
        )

        self.generic_visit(node)

    def _record_instance_bindings(
        self,
        node,
    ):
        targets = []

        if isinstance(node, ast.Assign):
            targets = node.targets

        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]

        value = getattr(
            node,
            "value",
            None,
        )

        if value is None:
            return

        class_name = self._constructor_name(
            value
        )

        if not class_name:
            return

        for target in targets:
            if not isinstance(
                target,
                ast.Attribute,
            ):
                continue

            if not isinstance(
                target.value,
                ast.Name,
            ):
                continue

            if target.value.id != "self":
                continue

            owner = self._current_class_owner()

            if owner:
                self.resolver._register_instance_binding(
                    owner=owner,
                    attribute=target.attr,
                    class_name=class_name,
                )

    def _constructor_name(
        self,
        node,
    ):
        if isinstance(node, ast.Call):
            function = node.func

            if isinstance(
                function,
                ast.Name,
            ):
                return function.id

            if isinstance(
                function,
                ast.Attribute,
            ):
                return function.attr

        return None

    def _current_class_owner(self):
        if not self.scope:
            return None

        if len(self.scope) >= 2:
            # scope = [ClassName, methodName]
            return (
                f"{self.file_path}:"
                f"{self.scope[0]}"
            )

        if len(self.scope) == 1:
            return (
                f"{self.file_path}:"
                f"{self.scope[0]}"
            )

        return None
