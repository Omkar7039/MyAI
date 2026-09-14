from dataclasses import dataclass
import re

from core.context import ContextManager
from core.model import LocalModel
from agents.debugging import DebugAgent
from router.intent_router import IntentRouter
from router.difficulty_router import DifficultyRouter
from router.model_router import ModelRouter
from tools.language_detector import LanguageDetector


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

    def __init__(self):
        self.model = LocalModel()

        self.context = ContextManager(
            max_messages=12,
            max_chars=12000,
        )

        self.router = IntentRouter()
        self.difficulty_router = DifficultyRouter()
        self.model_router = ModelRouter()

        self.language_detector = LanguageDetector()

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

    def handle(self, user_input: str) -> str:
        request = self.build_request(user_input)

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

            return self.debug_agent.analyze(
                problem=request.raw_text,
                code=request.code,
                language=request.language,
                auto_repair=True,
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
