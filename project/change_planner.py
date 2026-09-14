from dataclasses import dataclass, field


@dataclass
class ChangeTarget:
    file: str
    symbol: str
    reason: str


@dataclass
class ChangePlan:
    request: str
    targets: list[ChangeTarget] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)

    @property
    def files_count(self):
        return len(self.affected_files)

    @property
    def symbols_count(self):
        return len(self.targets)


class ChangePlanner:
    """
    Deterministic impact analysis for multi-file repair.

    This class does not modify source files and does not invoke the model.
    """

    def build_plan(
        self,
        context,
        request: str,
        symbols=None,
    ):
        if symbols is None:
            symbols = []

        symbols = self._select_change_symbols(
            symbols,
            request,
        )

        targets = self._build_targets(
            symbols,
            request,
        )

        affected_files = self._affected_files(
            context,
            targets,
        )

        dependencies = self._dependencies(
            context,
            affected_files,
        )

        dependents = self._dependents(
            context,
            affected_files,
        )

        flow = self._flow(
            context,
            targets,
        )

        return ChangePlan(
            request=request,
            targets=targets,
            affected_files=affected_files,
            dependencies=dependencies,
            dependents=dependents,
            flow=flow,
        )

    def _select_change_symbols(self, symbols, request):
        """
        Convert broad retrieval evidence into likely repair targets.

        Retrieval symbols may include classes, data containers, helpers,
        or the planner itself. Repair targets should be concrete
        application methods relevant to the requested behavior.
        """
        text = request.lower()

        preferred = []

        debug_request = any(
            word in text
            for word in [
                "debug",
                "bug",
                "error",
                "repair",
                "fix",
            ]
        )

        for symbol in symbols:
            name = (getattr(symbol, "name", "") or "").lower()
            parent = (getattr(symbol, "parent", "") or "").lower()
            file_path = (getattr(symbol, "file", "") or "").lower()

            # Never allow planner/tool internals to become repair targets.
            if (
                file_path.startswith("project/")
                and "change_planner" in file_path
            ):
                continue

            # Data containers are evidence, not repair targets.
            if name in {
                "request",
                "flowstep",
                "changetarget",
                "changeplan",
            }:
                continue

            score = 0

            if debug_request:
                if parent == "orchestrator" and name == "handle":
                    score += 100

                if parent == "orchestrator" and name == "build_request":
                    score += 80

                if parent == "debugagent" and name == "analyze":
                    score += 100

                if parent == "repairagent" and name == "repair_and_verify":
                    score += 90

                if parent == "repairagent" and name == "run_tests":
                    score += 60

                if parent == "repairagent" and name in {
                    "strengthen_tests",
                    "mutation_check",
                    "run_properties",
                    "generate_repair",
                }:
                    score += 40

            # Avoid selecting constructors/internal helpers unless nothing
            # more relevant exists.
            if name == "__init__":
                score -= 40

            if name.startswith("_"):
                score -= 10

            if score > 0:
                preferred.append((score, symbol))

        preferred.sort(
            key=lambda item: (
                -item[0],
                item[1].file,
                item[1].line,
            )
        )

        # Keep the actual change set intentionally small.
        return [
            symbol
            for _, symbol in preferred[:6]
        ]

    def _build_targets(self, symbols, request):
        targets = []

        for symbol in symbols:
            parent = getattr(symbol, "parent", None)
            name = getattr(symbol, "name", "")

            qualified = (
                f"{parent}.{name}"
                if parent
                else name
            )

            reason = self._reason(
                symbol,
                request,
            )

            targets.append(
                ChangeTarget(
                    file=symbol.file,
                    symbol=qualified,
                    reason=reason,
                )
            )

        return self._dedupe_targets(targets)

    def _reason(self, symbol, request):
        name = (getattr(symbol, "name", "") or "").lower()
        parent = (getattr(symbol, "parent", "") or "").lower()
        text = request.lower()

        if "debug" in text or "bug" in text or "error" in text:
            if parent == "debugagent":
                return "debug handling"

            if parent == "repairagent":
                return "repair pipeline"

            if name == "handle":
                return "request routing"

        if "repair" in text or "fix" in text:
            if parent == "repairagent":
                return "repair execution"

        return "request relevance"

    def _affected_files(self, context, targets):
        files = []

        for target in targets:
            files.append(target.file)

        # Preserve order and remove duplicates.
        return self._dedupe_strings(files)

    def _dependencies(self, context, files):
        results = []

        graph = getattr(
            context,
            "dependency_graph",
            None,
        )

        nodes = getattr(
            graph,
            "nodes",
            {},
        ) if graph else {}

        for file_path in files:
            node = nodes.get(file_path)

            if node is None:
                continue

            imports = getattr(
                node,
                "imports",
                set(),
            )

            for dependency in imports:
                results.append(dependency)

        return self._dedupe_strings(results)

    def _dependents(self, context, files):
        results = []

        graph = getattr(
            context,
            "dependency_graph",
            None,
        )

        nodes = getattr(
            graph,
            "nodes",
            {},
        ) if graph else {}

        for file_path in files:
            node = nodes.get(file_path)

            if node is None:
                continue

            imported_by = getattr(
                node,
                "imported_by",
                set(),
            )

            for dependent in imported_by:
                results.append(dependent)

        return self._dedupe_strings(results)

    def _flow(self, context, targets):
        results = []

        resolutions = getattr(
            context,
            "resolutions",
            [],
        )

        for target in targets:
            caller = f"{target.file}:{target.symbol}"

            for result in resolutions:
                result_caller = getattr(
                    result,
                    "caller",
                    "",
                )

                if result_caller != caller:
                    continue

                resolved_to = getattr(
                    result,
                    "resolved_to",
                    [],
                )

                for value in resolved_to:
                    results.append(
                        f"{caller} -> {value}"
                    )

        return self._dedupe_strings(results)

    def _dedupe_targets(self, targets):
        result = []
        seen = set()

        for target in targets:
            key = (
                target.file,
                target.symbol,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(target)

        return result

    def _dedupe_strings(self, values):
        result = []
        seen = set()

        for value in values:
            if value in seen:
                continue

            seen.add(value)
            result.append(value)

        return result
