from pathlib import Path

from core.model import LocalModel
from project.project_context import ProjectContextBuilder
from project.project_retriever import ProjectRetriever
from project.context_ranker import ContextRanker
from project.multi_file_analyzer import MultiFileAnalyzer
from memory.store import MemoryStore
from memory.retriever import MemoryRetriever
from memory.retriever import MemoryRetriever


class ProjectAgent:
    def __init__(self, model=None, root="~/MyAI"):
        self.model = model or LocalModel()
        self.root = Path(root).expanduser().resolve()

        self.context_builder = ProjectContextBuilder()
        self.retriever = ProjectRetriever(self.root)
        self.ranker = ContextRanker()
        self.flow_analyzer = MultiFileAnalyzer()
        self.memory_store = MemoryStore(
            self.root / "data" / "memory.db"
        )
        self.memory_retriever = MemoryRetriever(
            self.memory_store
        )

    def analyze(self, request: str):
        context = self.context_builder.build(self.root)

        evidence = self._collect_evidence(
            context=context,
            request=request,
        )

        prompt = self._build_prompt(
            request=request,
            context=context,
            evidence=evidence,
        )

        return self.model.ask(
            [{"role": "user", "content": prompt}],
            max_tokens=256,
        )

    def _collect_evidence(self, context, request):
        relevant_symbols = self._find_relevant_symbols(
            context=context,
            request=request,
        )

        relevant_symbols = self._add_flow_symbols(
            context=context,
            request=request,
            symbols=relevant_symbols,
        )

        relevant_symbols = self._dedupe_symbols(relevant_symbols)[:8]

        relevant_files = self._find_relevant_files(
            context=context,
            request=request,
            symbols=relevant_symbols,
        )

        source_bundle = self.retriever.read_related_sources(
            symbols=relevant_symbols,
            files=relevant_files,
        )

        source_bundle = self._apply_source_budget(
            source_bundle,
            max_chars=4500,
        )

        relationships = self._collect_relationships(
            context=context,
            symbols=relevant_symbols,
        )

        memory = self._collect_memory(
            request=request,
            max_results=6,
            max_chars=2400,
        )

        flow = self._build_verified_flow(
            context,
            request,
        )

        return {
            "symbols": relevant_symbols,
            "files": relevant_files,
            "source_bundle": source_bundle,
            "relationships": relationships,
            "memory": memory,
            "flow": flow,
        }

    def _collect_memory(
        self,
        request,
        max_results=6,
        max_chars=2400,
    ):
        """
        Retrieve persistent project-memory context.

        Memory is supplemental context. It is never treated as
        independently verified evidence.
        """
        results = self.memory_retriever.search(
            request,
            top_k=max_results,
        )

        selected = []
        used = 0

        for result in results:
            chunk = result.chunk

            text = (
                f"[{chunk.file_path}:{chunk.start_line}-"
                f"{chunk.end_line}] {chunk.kind}\n"
                f"{chunk.content}\n"
            )

            if used + len(text) > max_chars:
                continue

            selected.append(
                {
                    "file": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "kind": chunk.kind,
                    "score": result.score,
                    "content": chunk.content,
                }
            )

            used += len(text)

        return selected

    def _build_verified_flow(self, context, request):
        text = request.lower()

        start = "core/orchestrator.py:Orchestrator.handle"

        goals = []

        if any(
            word in text
            for word in [
                "debug",
                "debugging",
                "bug",
                "error",
                "repair",
                "fix",
                "trace",
            ]
        ):
            goals.append(
                "agents/debugging.py:DebugAgent.analyze"
            )

        if "repair" in text or "fix" in text:
            goals.append(
                "agents/repair.py:RepairAgent.repair_and_verify"
            )

        # Avoid sending a huge tree into the prompt.
        tree = self.flow_analyzer.analyze_branches(
            context,
            start,
            max_depth=4,
            max_children=4,
        )

        goal_paths = []

        for goal in goals:
            paths = self.flow_analyzer.analyze_flow(
                context,
                start_symbols=[start],
                goal_symbols=[goal],
                max_depth=8,
            )

            goal_paths.extend(paths)

        return {
            "start": start,
            "goals": goals,
            "tree": tree,
            "goal_paths": self.flow_analyzer._dedupe_traces(
                goal_paths
            ),
        }

    def _format_verified_flow(self, flow, max_lines=10):
        goal_paths = flow.get("goal_paths", [])

        if not goal_paths:
            return [
                "No verified execution flow was retrieved."
            ]

        # Merge common prefixes across verified goal paths.
        merged = list(goal_paths[0])

        for trace in goal_paths[1:]:
            common = 0

            while (
                common < len(merged)
                and common < len(trace)
                and merged[common] == trace[common]
            ):
                common += 1

            # Append only the new suffix.
            for symbol in trace[common:]:
                if symbol not in merged:
                    merged.append(symbol)

        lines = []

        for index, symbol in enumerate(merged):
            if len(lines) >= max_lines:
                lines.append("-> ... flow truncated ...")
                break

            prefix = "-> " if index == 0 else "   -> "
            lines.append(f"{prefix}{symbol}")

        # Explicitly preserve the known conditional repair branch.
        if (
            "agents/debugging.py:DebugAgent.analyze" in merged
            and "agents/repair.py:RepairAgent.repair_and_verify" in merged
        ):
            lines.append(
                "   -> [verified repair condition] "
                "agents/repair.py:RepairAgent.repair_and_verify"
            )

            # Remove an unconditional-looking duplicate.
            lines = [
                line
                for line in lines
                if line
                != "   -> agents/repair.py:RepairAgent.repair_and_verify"
            ]

        return lines

    def _find_relevant_symbols(self, context, request):
        symbols = []

        for file_index in context.code_index.files:
            symbols.extend(file_index.symbols)

        ranked = self.ranker.rank_symbols(
            symbols,
            request,
        )

        return [
            item.item
            for item in ranked[:12]
        ]

    def _add_flow_symbols(self, context, request, symbols):
        text = request.lower()

        important_names = set()

        if any(
            word in text
            for word in [
                "debug",
                "debugging",
                "error",
                "bug",
                "repair",
                "fix",
                "broken",
            ]
        ):
            important_names.update(
                {
                    "handle",
                    "build_request",
                    "analyze",
                    "repair_and_verify",
                    "run_tests",
                    "strengthen",
                    "evaluate_test_strength",
                }
            )

        if any(
            word in text
            for word in [
                "flow",
                "trace",
                "architecture",
                "request",
                "orchestration",
                "pipeline",
            ]
        ):
            important_names.update(
                {
                    "handle",
                    "build_request",
                    "analyze",
                    "route",
                }
            )

        if any(
            word in text
            for word in [
                "project",
                "repository",
                "codebase",
                "whole project",
                "entire project",
            ]
        ):
            important_names.update(
                {
                    "scan",
                    "build",
                    "analyze",
                }
            )

        if not important_names:
            return symbols

        indexed = {id(symbol): symbol for symbol in symbols}

        for file_index in context.code_index.files:
            for symbol in file_index.symbols:
                if symbol.name in important_names:
                    indexed[id(symbol)] = symbol

        return list(indexed.values())

    def _find_relevant_files(self, context, request, symbols):
        text = request.lower()

        files = []

        for symbol in symbols:
            files.append(symbol.file)

        # For debugging / repair, include the known execution path.
        if any(
            word in text
            for word in [
                "debug",
                "debugging",
                "repair",
                "fix",
                "bug",
                "error",
                "trace",
                "flow",
            ]
        ):
            preferred = [
                "core/orchestrator.py",
                "agents/debugging.py",
                "agents/repair.py",
                "tools/code_analyzer.py",
                "tools/runner_manager.py",
                "verification/test_generator.py",
                "verification/mutation_engine.py",
                "verification/test_strengthener.py",
                "verification/property_engine.py",
            ]

            files.extend(
                path
                for path in preferred
                if self._file_exists_in_context(context, path)
            )

        if any(
            word in text
            for word in [
                "router",
                "intent",
                "difficulty",
                "model",
            ]
        ):
            preferred = [
                "router/intent_router.py",
                "router/difficulty_router.py",
                "router/model_router.py",
                "models/registry.py",
            ]

            files.extend(
                path
                for path in preferred
                if self._file_exists_in_context(context, path)
            )

        unique = []
        seen = set()

        for path in files:
            if path in seen:
                continue

            seen.add(path)
            unique.append(path)

        return unique[:6]

    def _file_exists_in_context(self, context, relative_path):
        for file_index in context.code_index.files:
            if file_index.path == relative_path:
                return True

        return False

    def _apply_source_budget(self, source_bundle, max_chars=3200):
        used = 0

        selected_symbols = []
        selected_files = []

        per_symbol_limit = 900

        for item in source_bundle.get("symbols", []):
            source = item.get("source", "")

            if not source:
                continue

            source = source[:per_symbol_limit]

            if used + len(source) > max_chars:
                break

            copied = dict(item)
            copied["source"] = source

            selected_symbols.append(copied)
            used += len(source)

        for item in source_bundle.get("files", []):
            source = item.get("source", "")

            if used + len(source) > max_chars:
                continue

            selected_files.append(item)
            used += len(source)

        return {
            "symbols": selected_symbols,
            "files": selected_files,
        }

    def _collect_relationships(self, context, symbols):
        relationships = []

        relevant_callers = set()
        relevant_files = set()

        for symbol in symbols:
            caller_name = self._caller_name(symbol)

            relevant_callers.add(
                f"{symbol.file}:{caller_name}"
            )

            relevant_files.add(symbol.file)

        # First collect direct call-graph relationships for retrieved symbols.
        for edge in context.call_graph.edges:
            caller = getattr(edge, "caller", "")
            callee = getattr(edge, "callee", "")

            if caller in relevant_callers:
                relationships.append(
                    {
                        "type": "call",
                        "caller": caller,
                        "callee": callee,
                    }
                )

        # Add only resolved relationships belonging to retrieved callers.
        resolutions = getattr(context, "resolutions", {})

        if isinstance(resolutions, dict):
            for caller, resolved in resolutions.items():
                if caller not in relevant_callers:
                    continue

                for callee in resolved:
                    relationships.append(
                        {
                            "type": "resolved_call",
                            "caller": caller,
                            "callee": callee,
                        }
                    )

        relationships = self._dedupe_relationships(
            relationships
        )

        # Prefer project-internal relationships over library/external calls.
        def relationship_priority(item):
            callee = item["callee"]

            internal = (
                ".py:" in callee
                or callee.startswith("agents/")
                or callee.startswith("core/")
                or callee.startswith("project/")
                or callee.startswith("router/")
                or callee.startswith("tools/")
                or callee.startswith("verification/")
                or callee.startswith("models/")
            )

            return 0 if internal else 1

        relationships.sort(
            key=relationship_priority
        )

        # Keep the evidence bundle intentionally small.
        return relationships[:6]

    def _caller_name(self, symbol):
        parent = getattr(symbol, "parent", None)

        if parent:
            return f"{parent}.{symbol.name}"

        return symbol.name

    def _dedupe_symbols(self, symbols):
        unique = []
        seen = set()

        for symbol in symbols:
            key = (
                symbol.file,
                symbol.name,
                symbol.line,
                symbol.end_line,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(symbol)

        return unique

    def _dedupe_relationships(self, relationships):
        unique = []
        seen = set()

        for relationship in relationships:
            key = (
                relationship["type"],
                relationship["caller"],
                relationship["callee"],
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(relationship)

        return unique

    def _keywords(self, request):
        stopwords = {
            "the",
            "a",
            "an",
            "how",
            "what",
            "why",
            "where",
            "when",
            "does",
            "do",
            "is",
            "are",
            "my",
            "our",
            "this",
            "that",
            "me",
            "it",
            "in",
            "of",
            "to",
            "for",
            "and",
            "or",
            "with",
            "from",
            "by",
            "on",
            "as",
            "through",
            "please",
            "can",
            "you",
        }

        words = []

        for word in request.lower().replace("_", " ").split():
            word = word.strip(".,:;!?()[]{}\"'")

            if len(word) < 3:
                continue

            if word in stopwords:
                continue

            words.append(word)

        return words

    def _project_summary(self, context):
        code_index = getattr(context, "code_index", None)
        files = getattr(code_index, "files", []) if code_index else []

        language_counts = {}

        for file_index in files:
            language = getattr(file_index, "language", "unknown") or "unknown"
            language = language.lower()
            language_counts[language] = (
                language_counts.get(language, 0) + 1
            )

        return {
            "root": str(getattr(context, "root", self.root)),
            "indexed_files": len(files),
            "language_counts": language_counts,
        }

    def _build_prompt(self, request, context, evidence):
        summary = self._project_summary(context)

        sections = []

        sections.append(
            "You are MyAI's grounded project-analysis agent."
        )

        sections.append(
            "\nUSER REQUEST:\n"
            + request
        )

        sections.append(
            "\nPROJECT SUMMARY:\n"
            + str(summary)
        )

        sections.append(
            "\nVERIFIED SOURCE EVIDENCE:"
        )

        for item in evidence["source_bundle"]["symbols"]:
            qualified = item["file"]

            if item.get("parent"):
                qualified += f":{item['parent']}.{item['name']}"
            else:
                qualified += f":{item['name']}"

            sections.append(
                "\n"
                f"[SYMBOL] {qualified} "
                f"lines {item['line']}-{item['end_line']}\n"
                "```python\n"
                f"{item['source']}\n"
                "```"
            )

        sections.append(
            "\nVERIFIED WHOLE-FILE EVIDENCE:"
        )

        for item in evidence["source_bundle"]["files"]:
            sections.append(
                "\n"
                f"[FILE] {item['file']}\n"
                "```python\n"
                f"{item['source']}\n"
                "```"
            )

        sections.append(
            "\nPERSISTENT PROJECT MEMORY (SUPPLEMENTAL):"
        )

        memory_items = evidence.get("memory", [])

        if memory_items:
            for item in memory_items:
                sections.append(
                    "\n"
                    f"[MEMORY] {item['file']}:"
                    f"{item['start_line']}-{item['end_line']} "
                    f"{item['kind']} "
                    f"(retrieval_score={item['score']:.1f})\n"
                    "```python\n"
                    f"{item['content']}\n"
                    "```"
                )
        else:
            sections.append(
                "- No persistent memory context was retrieved."
            )

        sections.append(
            "\nVERIFIED EXECUTION FLOW:"
        )

        for line in self._format_verified_flow(
            evidence.get("flow"),
            max_lines=18,
        ):
            sections.append(line)

        sections.append(
            "\nVERIFIED CALL RELATIONSHIPS:"
        )

        if evidence["relationships"]:
            for relationship in evidence["relationships"]:
                sections.append(
                    f"- {relationship['caller']} "
                    f"-> {relationship['callee']}"
                )
        else:
            sections.append(
                "- No verified call relationship was retrieved."
            )

        sections.append(
            """
GROUNDING RULES:

1. Use the supplied source evidence as the authoritative evidence.
2. Do not invent files, functions, classes, calls, or dependencies.
3. Do not claim a relationship is verified unless it appears in the supplied relationships or source.
4. Clearly distinguish:
   - VERIFIED FACT
   - INFERENCE
5. When tracing execution, follow the supplied source and verified relationships.
6. Do not use unrelated files merely because their names sound relevant.
7. Treat PERSISTENT PROJECT MEMORY as supplemental retrieval context only.
8. A memory chunk alone does not establish a VERIFIED FACT.
9. Prefer VERIFIED SOURCE EVIDENCE and VERIFIED RELATIONSHIPS over memory context when they disagree.
10. If the supplied evidence is insufficient, explicitly say what cannot be verified.
11. Prefer exact file paths and symbol names in the answer.
"""
        )

        return "\n".join(sections)
