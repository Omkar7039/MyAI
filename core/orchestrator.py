from tools.runner_manager import RunnerManager
from tools.registry import ToolRegistry
from tools.execution_tool import ExecutionTool
from tools.file_tool import ReadFileTool
from tools.list_files_tool import ListFilesTool
from tools.search_files_tool import SearchFilesTool
from tools.workspace import Workspace
from tools.write_file_tool import WriteFileTool
from tools.edit_file_tool import EditFileTool
from tools.delete_file_tool import DeleteFileTool
from tools.create_directory_tool import CreateDirectoryTool
from tools.move_file_tool import MoveFileTool
from tools.copy_file_tool import CopyFileTool
from tools.get_file_info_tool import GetFileInfoTool
from tools.directory_tree_tool import DirectoryTreeTool
from tools.file_exists_tool import FileExistsTool
from tools.file_hash_tool import FileHashTool
from tools.base import ToolParameter, ToolSchema, ToolResult
from tools.result_normalizer import ToolResultNormalizer
from tools.execution_trace import ToolExecutionTracer
from tools.policy import create_default_tool_policy_registry
from tools.policy_guard import (
    ToolExecutionMode,
    ToolPolicyGuard,
)
from tools.policy_guard import ToolPolicyGuard
from dataclasses import dataclass
from uuid import uuid4
import re

from core.context import ContextManager
from core.model import LocalModel
from agents.debugging import DebugAgent
from router.intent_router import IntentRouter
from router.difficulty_router import DifficultyRouter
from router.model_router import ModelRouter
from tools.language_detector import LanguageDetector
from experience.learning_orchestrator import UnifiedLearningRouter
from experience.governed_strategy_router import GovernedStrategyRouter
from experience.learning_signal import LearningSignal
from core.task_supervisor import TaskExecution, TaskSupervisor
from core.tool_decision_engine import ToolDecisionEngine
from core.tool_result_observer import ToolResultObserver


@dataclass
class Request:
    """
    Structured representation of a MyAI request.
    """

    raw_text: str
    intent: str
    confidence: float
    code: str | None
    language: str
    difficulty: str
    difficulty_score: int
    difficulty_reasons: list[str]


class Orchestrator:
    """
    Central intelligence controller.

    Pipeline:

        User
          ↓
        Context
          ↓
        Intent Router
          ↓
        Code extraction
          ↓
        Language detection
          ↓
        Difficulty Router
          ↓
        Model Router
          ↓
        Agent
          ↓
        Tools
          ↓
        Verification
    """

    def __init__(
        self,
        *,
        tool_execution_mode: ToolExecutionMode = (
            ToolExecutionMode.PERMISSIVE
        ),
    ):
        self.model = LocalModel()

        self.context = ContextManager(
            max_messages=12,
            max_chars=12000,
        )

        self.router = IntentRouter()
        self.difficulty_router = DifficultyRouter()
        self.model_router = ModelRouter()

        self.language_detector = LanguageDetector()
        self.runner_manager = RunnerManager()

        self.tool_registry = ToolRegistry()
        self.tool_decision_engine = ToolDecisionEngine()
        self.tool_result_observer = ToolResultObserver()
        self.tool_tracer = ToolExecutionTracer()
        self.tool_policy_registry = (
            create_default_tool_policy_registry()
        )

        self.tool_policy_guard = ToolPolicyGuard(
            self.tool_policy_registry,
            mode=tool_execution_mode,
        )

        self.execution_tool = ExecutionTool(
            self.runner_manager
        )

        self.workspace = Workspace()

        self.read_file_tool = ReadFileTool(
            workspace=self.workspace
        )
        self.list_files_tool = ListFilesTool(
            workspace=self.workspace
        )
        self.search_files_tool = SearchFilesTool(
            workspace=self.workspace
        )
        self.write_file_tool = WriteFileTool(
            workspace=self.workspace
        )
        self.edit_file_tool = EditFileTool(
            workspace=self.workspace
        )
        self.delete_file_tool = DeleteFileTool(
            workspace=self.workspace
        )
        self.move_file_tool = MoveFileTool(
            workspace=self.workspace
        )
        self.copy_file_tool = CopyFileTool(
            workspace=self.workspace
        )
        self.get_file_info_tool = GetFileInfoTool(
            workspace=self.workspace
        )
        self.directory_tree_tool = DirectoryTreeTool(
            workspace=self.workspace
        )
        self.file_exists_tool = FileExistsTool(
            workspace=self.workspace
        )
        self.file_hash_tool = FileHashTool(
            workspace=self.workspace
        )
        self.create_directory_tool = CreateDirectoryTool(
            workspace=self.workspace
        )

        self.tool_registry.register(
            self.execution_tool.name,
            self.execution_tool.execute,
            description=self.execution_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="code",
                        parameter_type="string",
                        description="Source code to execute.",
                    ),
                    ToolParameter(
                        name="language",
                        parameter_type="string",
                        description="Programming language.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.read_file_tool.name,
            self.read_file_tool.execute,
            description=self.read_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="Path of the text file to read.",
                    ),
                    ToolParameter(
                        name="start_line",
                        parameter_type="integer",
                        required=False,
                        description="Optional 1-based starting line.",
                    ),
                    ToolParameter(
                        name="end_line",
                        parameter_type="integer",
                        required=False,
                        description="Optional 1-based ending line.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.list_files_tool.name,
            self.list_files_tool.execute,
            description=self.list_files_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        required=False,
                        description="Directory to inspect.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.search_files_tool.name,
            self.search_files_tool.execute,
            description=self.search_files_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="query",
                        parameter_type="string",
                        description="Text to search for.",
                    ),
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        required=False,
                        description="Directory or file to search.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.write_file_tool.name,
            self.write_file_tool.execute,
            description=self.write_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="Path of the file to write.",
                    ),
                    ToolParameter(
                        name="content",
                        parameter_type="string",
                        description="Text content to write.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.edit_file_tool.name,
            self.edit_file_tool.execute,
            description=self.edit_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="Path of the file to edit.",
                    ),
                    ToolParameter(
                        name="old_text",
                        parameter_type="string",
                        description="Exact text to replace.",
                    ),
                    ToolParameter(
                        name="new_text",
                        parameter_type="string",
                        description="Replacement text.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.delete_file_tool.name,
            self.delete_file_tool.execute,
            description=self.delete_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="Path of the file to delete.",
                    ),
                ),
            ),
        )

        self.tool_registry.register(
            self.create_directory_tool.name,
            self.create_directory_tool.execute,
            description=self.create_directory_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="Directory path to create.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.move_file_tool.name,
            self.move_file_tool.execute,
            description=self.move_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="source",
                        parameter_type="string",
                        description="Source file or directory path.",
                    ),
                    ToolParameter(
                        name="destination",
                        parameter_type="string",
                        description="Destination file or directory path.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.copy_file_tool.name,
            self.copy_file_tool.execute,
            description=self.copy_file_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="source",
                        parameter_type="string",
                        description="Source file or directory path.",
                    ),
                    ToolParameter(
                        name="destination",
                        parameter_type="string",
                        description="Destination file or directory path.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.get_file_info_tool.name,
            self.get_file_info_tool.execute,
            description=self.get_file_info_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="File or directory path to inspect.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.directory_tree_tool.name,
            self.directory_tree_tool.execute,
            description=self.directory_tree_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        required=False,
                        description="Directory path to inspect.",
                    ),
                    ToolParameter(
                        name="max_depth",
                        parameter_type="integer",
                        required=False,
                        description="Maximum directory depth to inspect.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.file_exists_tool.name,
            self.file_exists_tool.execute,
            description=self.file_exists_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="File or directory path to check.",
                    ),
                ),
            ),
        )
        self.tool_registry.register(
            self.file_hash_tool.name,
            self.file_hash_tool.execute,
            description=self.file_hash_tool.description,
            schema=ToolSchema(
                parameters=(
                    ToolParameter(
                        name="path",
                        parameter_type="string",
                        description="File path to hash.",
                    ),
                ),
            ),
        )

        self.learning_router = UnifiedLearningRouter()
        self.governed_learning_router = GovernedStrategyRouter()

        self.debug_agent = DebugAgent(self.model)

    def extract_code(self, text: str) -> str | None:
        """
        Extract code from fenced blocks, inline code, or multiline code.
        """

        cleaned = text.strip()

        if not cleaned:
            return None

        if cleaned.lower().startswith("/debug"):
            cleaned = cleaned[6:].strip()

        # --------------------------------------------------
        # Fenced code
        # --------------------------------------------------
        if "```" in cleaned:
            parts = cleaned.split("```")

            if len(parts) >= 3:
                block = parts[1].strip()
                lines = block.splitlines()

                language_names = {
                    "python",
                    "javascript",
                    "typescript",
                    "java",
                    "c",
                    "cpp",
                    "c++",
                    "csharp",
                    "c#",
                    "go",
                    "rust",
                    "php",
                    "ruby",
                    "bash",
                    "shell",
                    "powershell",
                    "sql",
                }

                if (
                    lines
                    and lines[0].strip().lower()
                    in language_names
                ):
                    lines = lines[1:]

                code = "\n".join(lines).strip()

                if code:
                    return code

        # --------------------------------------------------
        # Inline code after code/program/script/source:
        # --------------------------------------------------
        inline_match = re.search(
            r"(?:code|program|script|source)\s*:\s*(.+)$",
            cleaned,
            re.IGNORECASE | re.DOTALL,
        )

        if inline_match:
            candidate = inline_match.group(1).strip()
            candidate = candidate.strip("`")

            if candidate:
                code_signals = (
                    r"\bdef\s+\w+\s*\(",
                    r"\bfunction\s+\w+\s*\(",
                    r"\bconsole\.(log|error|warn)\s*\(",
                    r"\b(?:const|let|var)\s+\w+\s*=",
                    r"\bprint\s*\(",
                    r"#include\s*[<\"]",
                    r"\bpublic\s+class\s+",
                )

                for pattern in code_signals:
                    if re.search(
                        pattern,
                        candidate,
                        re.IGNORECASE,
                    ):
                        return candidate

        # --------------------------------------------------
        # Plain multiline code
        # --------------------------------------------------
        lines = cleaned.splitlines()

        code_lines = []
        started = False

        code_starters = (
            "def ",
            "class ",
            "import ",
            "from ",
            "print(",
            "if ",
            "for ",
            "while ",
            "function ",
            "const ",
            "let ",
            "var ",
            "#include",
            "public class ",
            "package ",
            "fn main",
            "<?php",
            "select ",
            "insert ",
            "update ",
            "delete ",
        )

        for line in lines:
            stripped = line.strip()

            if not started:
                if stripped.startswith(code_starters):
                    started = True
                else:
                    continue

            if stripped.upper() == "END":
                continue

            code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines).strip()

        # --------------------------------------------------
        # Raw one-line code
        # --------------------------------------------------
        raw_code_signals = (
            r"\bdef\s+\w+\s*\(",
            r"\bfunction\s+\w+\s*\(",
            r"\bconsole\.(log|error|warn)\s*\(",
            r"\b(?:const|let|var)\s+\w+\s*=",
            r"\bprint\s*\(",
            r"#include\s*[<\"]",
        )

        for pattern in raw_code_signals:
            if re.search(
                pattern,
                cleaned,
                re.IGNORECASE,
            ):
                return cleaned

        return None

    def detect_language(
        self,
        text: str,
        code: str | None,
    ) -> str:
        """
        Detect explicit language mentions first, then extracted code.
        """

        lower = text.lower()

        aliases = {
            "python": "python",
            "javascript": "javascript",
            "node.js": "javascript",
            "nodejs": "javascript",
            "typescript": "typescript",
            "java": "java",
            "cpp": "cpp",
            "c++": "cpp",
            "csharp": "csharp",
            "c#": "csharp",
            "go": "go",
            "golang": "go",
            "rust": "rust",
            "php": "php",
            "ruby": "ruby",
            "bash": "bash",
            "shell": "bash",
            "powershell": "powershell",
            "sql": "sql",
        }

        for name, normalized in aliases.items():
            if name in lower:
                return normalized

        if code:
            detected = self.language_detector.detect(code)

            if detected != "unknown":
                return detected

            detected = self.language_detector.detect(text)

            if detected != "unknown":
                return detected

        return "unknown"

    def build_request(self, user_input: str) -> Request:
        intent = self.router.route(user_input)

        code = self.extract_code(user_input)

        language = self.detect_language(
            user_input,
            code,
        )

        if code and intent.name == "question":
            intent_name = "code_analysis"
            confidence = 0.82
        else:
            intent_name = intent.name
            confidence = intent.confidence

        difficulty = self.difficulty_router.analyze(
            text=user_input,
            code=code,
            language=language,
        )

        return Request(
            raw_text=user_input,
            intent=intent_name,
            confidence=confidence,
            code=code,
            language=language,
            difficulty=difficulty.level,
            difficulty_score=difficulty.score,
            difficulty_reasons=difficulty.reasons,
        )

    def execute_code(
        self,
        code: str,
        language: str,
    ):
        """
        Execute supplied code through the controlled runner layer.

        Execution is explicit and never happens automatically during
        normal request handling.
        """

        if not code.strip():
            raise ValueError("No code supplied for execution.")

        if language == "unknown":
            raise ValueError(
                "Cannot execute code because the language is unknown."
            )

        if not self.runner_manager.supports(language):
            raise ValueError(
                f"No execution runner is installed for: {language}"
            )

        return self.runner_manager.run(
            language,
            code,
        )


    def handle(
        self,
        user_input: str,
        learning_signals: tuple[LearningSignal, ...]
        | list[LearningSignal] = (),
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        task_family: str | None = None,
        allow_cross_task: bool = False,
    ) -> str:
        request = self.build_request(user_input)

        learning_route = self.learning_router.route(
            default_repair_strategy="standard",
            default_verification_strategy="standard",
            signals=learning_signals,
            utility_by_strategy=utility_by_strategy,
        )

        governed_repair = None
        governed_verification = None

        if baseline_score_by_strategy is not None:
            repair_baseline = baseline_score_by_strategy.get(
                learning_route.repair.strategy
            )

            verification_baseline = baseline_score_by_strategy.get(
                learning_route.verification.strategy
            )

            if repair_baseline is not None:
                governed_repair = self.governed_learning_router.route(
                    default_strategy=learning_route.repair.strategy,
                    signals=learning_signals,
                    baseline_score=repair_baseline,
                    task_family=task_family,
                    allow_cross_task=allow_cross_task,
                    utility_by_strategy=utility_by_strategy,
                )

            if verification_baseline is not None:
                governed_verification = (
                    self.governed_learning_router.route(
                        default_strategy=learning_route.verification.strategy,
                        signals=learning_signals,
                        baseline_score=verification_baseline,
                        task_family=task_family,
                        allow_cross_task=allow_cross_task,
                        utility_by_strategy=utility_by_strategy,
                    )
                )

        model_profile = self._choose_model(request)

        print(
            f"\n[MyAI] Intent={request.intent} "
            f"Confidence={request.confidence:.2f}"
        )

        print(
            f"[MyAI] Language={request.language} "
            f"Difficulty={request.difficulty} "
            f"Score={request.difficulty_score}"
        )

        print(
            f"[MyAI] Model={model_profile.name}"
        )

        if request.difficulty_reasons:
            print(
                "[MyAI] Complexity signals="
                + ", ".join(request.difficulty_reasons)
            )

        # --------------------------------------------------
        # DEBUG / REPAIR
        # --------------------------------------------------
        if request.intent in {"debug", "repair"}:
            print("[MyAI] Agent=DebugAgent")

            print(
                f"[MyAI] LearningRepairStrategy="
                f"{learning_route.repair.strategy} "
                f"Learned={learning_route.repair.learned}"
            )

            print(
                f"[MyAI] LearningVerificationStrategy="
                f"{learning_route.verification.strategy} "
                f"Learned={learning_route.verification.learned}"
            )

            if governed_repair is not None:
                print(
                    f"[MyAI] GovernedRepairStrategy="
                    f"{governed_repair.strategy} "
                    f"Learned={governed_repair.learned} "
                    f"Governed={governed_repair.governed}"
                )

            if governed_verification is not None:
                print(
                    f"[MyAI] GovernedVerificationStrategy="
                    f"{governed_verification.strategy} "
                    f"Learned={governed_verification.learned} "
                    f"Governed={governed_verification.governed}"
                )

            repair_strategy = learning_route.repair.strategy

            if governed_repair is not None:
                repair_strategy = governed_repair.strategy

            return self.debug_agent.analyze(
                problem=request.raw_text,
                code=request.code,
                language=request.language,
                auto_repair=True,
                repair_strategy=repair_strategy,
            )

        # --------------------------------------------------
        # REFACTOR
        # --------------------------------------------------
        if request.intent == "refactor":
            if not request.code:
                return self.model.ask(
                    [
                        {
                            "role": "user",
                            "content": request.raw_text,
                        }
                    ],
                    max_tokens=self._max_tokens_for(request),
                )

            print("[MyAI] Agent=RefactorAgent")

            prompt = (
                "You are MyAI's Code Improvement Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Improve the supplied code.\n"
                "Preserve behavior unless the user asks for a "
                "behavior change.\n"
                "Make it cleaner, simpler and maintainable.\n"
                "Only make performance changes when justified.\n"
                "Return complete improved code.\n"
                "Explain important changes.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE REVIEW
        # --------------------------------------------------
        if request.intent == "review":
            print("[MyAI] Agent=ReviewAgent")

            prompt = (
                "You are MyAI's Code Review Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Review the supplied code for:\n"
                "- correctness\n"
                "- bugs\n"
                "- security\n"
                "- maintainability\n"
                "- performance\n"
                "- error handling\n\n"
                "Do not invent problems.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE ANALYSIS
        # --------------------------------------------------
        if request.intent in {
            "analysis",
            "code_analysis",
        }:
            print("[MyAI] Agent=AnalysisAgent")

            prompt = (
                "You are MyAI's Code Analysis Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Analyze the supplied code accurately.\n"
                "Explain structure, control flow, important functions, "
                "dependencies, possible bugs, and complexity.\n"
                "Do not invent behavior that is not supported by the code.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code or request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE GENERATION
        # --------------------------------------------------
        if request.intent == "code_generation":
            print("[MyAI] Agent=CodeGenerationAgent")

            prompt = (
                "You are MyAI's Code Generation Agent.\n\n"
                "Generate correct, clean, maintainable code.\n"
                "Explain important design decisions briefly.\n"
                "Do not invent unavailable dependencies.\n\n"
                f"User request:\n{request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # PROJECT
        # --------------------------------------------------
        if request.intent == "project":
            print("[MyAI] Agent=ProjectAgent")

            prompt = (
                "You are MyAI's Project/Architecture Agent.\n\n"
                "Analyze the user's project or architecture request.\n"
                "Reason about components, dependencies, failure points, "
                "scalability, reliability, security, and implementation "
                "strategy.\n\n"
                f"User request:\n{request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # NORMAL CONVERSATION
        # --------------------------------------------------
        self.context.add(
            "user",
            request.raw_text,
        )

        response = self.model.ask(
            self.context.get(),
            max_tokens=self._max_tokens_for(request),
        )

        self.context.add(
            "assistant",
            response,
        )

        return response

    def handle_supervised(
        self,
        user_input: str,
        *,
        task_id: str | None = None,
        learning_signals: tuple[LearningSignal, ...]
        | list[LearningSignal] = (),
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        task_family: str | None = None,
        allow_cross_task: bool = False,
    ) -> tuple[str, TaskExecution]:
        """
        Execute one top-level request under TaskSupervisor control.

        The existing handle() contract remains unchanged.
        """
        supervisor = TaskSupervisor()

        resolved_task_id = (
            task_id
            or f"task-{uuid4().hex}"
        )

        supervisor.create(resolved_task_id)
        supervisor.start(resolved_task_id)

        try:
            response = self.handle(
                user_input,
                learning_signals=learning_signals,
                utility_by_strategy=utility_by_strategy,
                baseline_score_by_strategy=baseline_score_by_strategy,
                task_family=task_family,
                allow_cross_task=allow_cross_task,
            )

        except KeyboardInterrupt:
            execution = supervisor.stop(
                resolved_task_id,
                "task interrupted",
            )
            return "", execution

        except Exception as exc:
            execution = supervisor.fail(
                resolved_task_id,
                f"top-level task failed: {exc}",
            )
            raise RuntimeError(
                f"MyAI task {resolved_task_id} failed"
            ) from exc

        execution = supervisor.complete(
            resolved_task_id,
        )

        return response, execution

    def decide_tool(self, request: str):
        return self.tool_decision_engine.decide(request)

    def observe_tool_result(self, execution_plan):
        return self.tool_result_observer.observe(execution_plan)

    def invoke_tool(
        self,
        tool_name,
        *args,
        **kwargs,
    ):
        normalized_name = tool_name.strip().lower()

        if (
            normalized_name == self.execution_tool.name
            and args
            and not kwargs
        ):
            if len(args) != 2:
                raise ValueError(
                    "execute_code requires code and language."
                )

            kwargs = {
                "code": args[0],
                "language": args[1],
            }
            args = ()

        self.tool_policy_guard.check(
            normalized_name
        )

        started = self.tool_tracer.time()

        try:
            result = self.tool_registry.invoke(
                tool_name,
                *args,
                **kwargs,
            )

            duration_ms = (
                self.tool_tracer.time() - started
            ) * 1000

            success = (
                result.success
                if isinstance(result, ToolResult)
                else True
            )

            error = (
                result.error
                if isinstance(result, ToolResult)
                else None
            )

            self.tool_tracer.record(
                tool_name=normalized_name,
                success=success,
                duration_ms=duration_ms,
                error=error,
            )

            return result

        except ValueError as exc:
            duration_ms = (
                self.tool_tracer.time() - started
            ) * 1000

            if normalized_name == "read_file":
                self.tool_tracer.record(
                    tool_name=normalized_name,
                    success=False,
                    duration_ms=duration_ms,
                    error=str(exc),
                )

                return ToolResult(
                    tool_name=normalized_name,
                    success=False,
                    error=str(exc),
                )

            raise

    def invoke_tool_normalized(
        self,
        tool_name,
        *args,
        **kwargs,
    ):
        """
        Invoke a tool and normalize its result for downstream consumers.
        """
        result = self.invoke_tool(
            tool_name,
            *args,
            **kwargs,
        )

        return ToolResultNormalizer.normalize(result)

    def get_tool_traces(self):
        """
        Return the recorded tool execution traces.
        """
        return self.tool_tracer.traces()

    def clear_tool_traces(self) -> None:
        """
        Clear all recorded tool execution traces.
        """
        self.tool_tracer.clear()



    def _choose_model(self, request: Request):
        return self.model_router.choose(
            request.difficulty
        )

    def _max_tokens_for(self, request: Request) -> int:
        limits = {
            "easy": 384,
            "medium": 512,
            "hard": 768,
            "expert": 1024,
        }

        return limits.get(
            request.difficulty,
            512,
        )

def observe_tool_result(self, execution_plan):
    return self.tool_result_observer.observe(execution_plan)

    def handle_supervised(
        self,
        user_input: str,
        *,
        task_id: str | None = None,
        learning_signals: tuple[LearningSignal, ...]
        | list[LearningSignal] = (),
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        task_family: str | None = None,
        allow_cross_task: bool = False,
    ) -> tuple[str, TaskExecution]:
        """
        Execute one top-level request under TaskSupervisor control.

        The existing handle() contract remains unchanged.
        """
        supervisor = TaskSupervisor()

        resolved_task_id = (
            task_id
            or f"task-{uuid4().hex}"
        )

        supervisor.create(resolved_task_id)
        supervisor.start(resolved_task_id)

        try:
            response = self.handle(
                user_input,
                learning_signals=learning_signals,
                utility_by_strategy=utility_by_strategy,
                baseline_score_by_strategy=baseline_score_by_strategy,
                task_family=task_family,
                allow_cross_task=allow_cross_task,
            )

        except KeyboardInterrupt:
            execution = supervisor.stop(
                resolved_task_id,
                "task interrupted",
            )
            return "", execution

        except Exception as exc:
            execution = supervisor.fail(
                resolved_task_id,
                f"top-level task failed: {exc}",
            )
            raise RuntimeError(
                f"MyAI task {resolved_task_id} failed"
            ) from exc

        execution = supervisor.complete(
            resolved_task_id,
        )

        return response, execution


    def handle(
        self,
        user_input: str,
        learning_signals: tuple[LearningSignal, ...]
        | list[LearningSignal] = (),
        utility_by_strategy: dict[str, float] | None = None,
        baseline_score_by_strategy: dict[str, float] | None = None,
        task_family: str | None = None,
        allow_cross_task: bool = False,
    ) -> str:
        request = self.build_request(user_input)

        learning_route = self.learning_router.route(
            default_repair_strategy="standard",
            default_verification_strategy="standard",
            signals=learning_signals,
            utility_by_strategy=utility_by_strategy,
        )

        governed_repair = None
        governed_verification = None

        if baseline_score_by_strategy is not None:
            repair_baseline = baseline_score_by_strategy.get(
                learning_route.repair.strategy
            )

            verification_baseline = baseline_score_by_strategy.get(
                learning_route.verification.strategy
            )

            if repair_baseline is not None:
                governed_repair = self.governed_learning_router.route(
                    default_strategy=learning_route.repair.strategy,
                    signals=learning_signals,
                    baseline_score=repair_baseline,
                    task_family=task_family,
                    allow_cross_task=allow_cross_task,
                    utility_by_strategy=utility_by_strategy,
                )

            if verification_baseline is not None:
                governed_verification = (
                    self.governed_learning_router.route(
                        default_strategy=learning_route.verification.strategy,
                        signals=learning_signals,
                        baseline_score=verification_baseline,
                        task_family=task_family,
                        allow_cross_task=allow_cross_task,
                        utility_by_strategy=utility_by_strategy,
                    )
                )

        model_profile = self._choose_model(request)

        print(
            f"\n[MyAI] Intent={request.intent} "
            f"Confidence={request.confidence:.2f}"
        )

        print(
            f"[MyAI] Language={request.language} "
            f"Difficulty={request.difficulty} "
            f"Score={request.difficulty_score}"
        )

        print(
            f"[MyAI] Model={model_profile.name}"
        )

        if request.difficulty_reasons:
            print(
                "[MyAI] Complexity signals="
                + ", ".join(request.difficulty_reasons)
            )

        # --------------------------------------------------
        # DEBUG / REPAIR
        # --------------------------------------------------
        if request.intent in {"debug", "repair"}:
            print("[MyAI] Agent=DebugAgent")

            print(
                f"[MyAI] LearningRepairStrategy="
                f"{learning_route.repair.strategy} "
                f"Learned={learning_route.repair.learned}"
            )

            print(
                f"[MyAI] LearningVerificationStrategy="
                f"{learning_route.verification.strategy} "
                f"Learned={learning_route.verification.learned}"
            )

            if governed_repair is not None:
                print(
                    f"[MyAI] GovernedRepairStrategy="
                    f"{governed_repair.strategy} "
                    f"Learned={governed_repair.learned} "
                    f"Governed={governed_repair.governed}"
                )

            if governed_verification is not None:
                print(
                    f"[MyAI] GovernedVerificationStrategy="
                    f"{governed_verification.strategy} "
                    f"Learned={governed_verification.learned} "
                    f"Governed={governed_verification.governed}"
                )

            repair_strategy = learning_route.repair.strategy

            if governed_repair is not None:
                repair_strategy = governed_repair.strategy

            return self.debug_agent.analyze(
                problem=request.raw_text,
                code=request.code,
                language=request.language,
                auto_repair=True,
                repair_strategy=repair_strategy,
            )

        # --------------------------------------------------
        # REFACTOR
        # --------------------------------------------------
        if request.intent == "refactor":
            if not request.code:
                return self.model.ask(
                    [
                        {
                            "role": "user",
                            "content": request.raw_text,
                        }
                    ],
                    max_tokens=self._max_tokens_for(request),
                )

            print("[MyAI] Agent=RefactorAgent")

            prompt = (
                "You are MyAI's Code Improvement Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Improve the supplied code.\n"
                "Preserve behavior unless the user asks for a "
                "behavior change.\n"
                "Make it cleaner, simpler and maintainable.\n"
                "Only make performance changes when justified.\n"
                "Return complete improved code.\n"
                "Explain important changes.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE REVIEW
        # --------------------------------------------------
        if request.intent == "review":
            print("[MyAI] Agent=ReviewAgent")

            prompt = (
                "You are MyAI's Code Review Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Review the supplied code for:\n"
                "- correctness\n"
                "- bugs\n"
                "- security\n"
                "- maintainability\n"
                "- performance\n"
                "- error handling\n\n"
                "Do not invent problems.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE ANALYSIS
        # --------------------------------------------------
        if request.intent in {
            "analysis",
            "code_analysis",
        }:
            print("[MyAI] Agent=AnalysisAgent")

            prompt = (
                "You are MyAI's Code Analysis Agent.\n\n"
                f"Programming language: {request.language}\n\n"
                "Analyze the supplied code accurately.\n"
                "Explain structure, control flow, important functions, "
                "dependencies, possible bugs, and complexity.\n"
                "Do not invent behavior that is not supported by the code.\n\n"
                f"User request:\n{request.raw_text}\n\n"
                f"Code:\n{request.code or request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # CODE GENERATION
        # --------------------------------------------------
        if request.intent == "code_generation":
            print("[MyAI] Agent=CodeGenerationAgent")

            prompt = (
                "You are MyAI's Code Generation Agent.\n\n"
                "Generate correct, clean, maintainable code.\n"
                "Explain important design decisions briefly.\n"
                "Do not invent unavailable dependencies.\n\n"
                f"User request:\n{request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # PROJECT
        # --------------------------------------------------
        if request.intent == "project":
            print("[MyAI] Agent=ProjectAgent")

            prompt = (
                "You are MyAI's Project/Architecture Agent.\n\n"
                "Analyze the user's project or architecture request.\n"
                "Reason about components, dependencies, failure points, "
                "scalability, reliability, security, and implementation "
                "strategy.\n\n"
                f"User request:\n{request.raw_text}\n"
            )

            return self.model.ask(
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=self._max_tokens_for(request),
            )

        # --------------------------------------------------
        # NORMAL CONVERSATION
        # --------------------------------------------------
        self.context.add(
            "user",
            request.raw_text,
        )

        response = self.model.ask(
            self.context.get(),
            max_tokens=self._max_tokens_for(request),
        )

        self.context.add(
            "assistant",
            response,
        )

        return response
