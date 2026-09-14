from dataclasses import dataclass
import re


@dataclass
class Intent:
    name: str
    confidence: float


class IntentRouter:
    """
    Fast local intent router.

    Stage 1:
    - deterministic
    - no LLM call
    - designed to handle natural variations
    """

    PROJECT_PATTERNS = (
        "repository",
        "repo",
        "codebase",
        "whole project",
        "entire project",
        "scan the project",
        "analyze the project",
        "analyse the project",
    "architecture",
    "microservice architecture",
    "distributed architecture",
    "system architecture",
    "analyze this architecture",
    "analyse this architecture",
    "analyze the architecture",
    "analyse the architecture",
    )

    DEBUG_PATTERNS = (
        "debug",
        "debugging",
        "bug",
        "error",
        "exception",
        "crash",
        "crashes",
        "traceback",
        "fails",
        "failure",
        "not working",
        "broken",
        "troubleshoot",
    )

    REPAIR_PATTERNS = (
        "repair",
        "fix this",
        "fix the code",
        "fix my code",
        "correct this code",
        "correct the code",
        "correct this",
    )

    REVIEW_PATTERNS = (
        "review this code",
        "review the code",
        "code review",
        "review my code",
        "security review",
    )

    ANALYSIS_PATTERNS = (
        "analyze this code",
        "analyse this code",
        "analyze the code",
        "analyse the code",
        "explain this code",
        "explain the code",
        "how does this code work",
        "understand this code",
    )

    CODE_GENERATION_PATTERNS = (
        "write a",
        "write an",
        "write code",
        "create a function",
        "create a class",
        "create an api",
        "create a program",
        "generate code",
        "generate a function",
        "implement",
        "build a function",
        "build an api",
    )

    def route(self, text: str) -> Intent:
        value = self._normalize(text)

        if not value:
            return Intent("empty", 1.0)

        # Project has highest priority.
        if self._contains(value, self.PROJECT_PATTERNS):
            return Intent("project", 0.98)

        # Explicit debugging.
        if self._contains(value, self.DEBUG_PATTERNS):
            return Intent("debug", 0.98)

        # Explicit repair.
        if self._contains(value, self.REPAIR_PATTERNS):
            return Intent("repair", 0.97)

        # Flexible refactor detection.
        if self._is_refactor_request(value):
            return Intent("refactor", 0.96)

        if self._contains(value, self.REVIEW_PATTERNS):
            return Intent("review", 0.95)

        if self._contains(value, self.ANALYSIS_PATTERNS):
            return Intent("analysis", 0.95)

        if self._contains(value, self.CODE_GENERATION_PATTERNS):
            return Intent("code_generation", 0.93)

        if self._looks_like_code(value):
            return Intent("code_analysis", 0.82)

        return Intent("question", 0.70)

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _contains(
        text: str,
        patterns: tuple[str, ...],
    ) -> bool:
        return any(pattern in text for pattern in patterns)

    @staticmethod
    def _is_refactor_request(text: str) -> bool:
        """
        Detect refactoring requests with flexible wording.

        Examples:
        - make this code shorter
        - make this code cleaner
        - make the code simpler
        - simplify this code
        - optimize the code
        - clean up this code
        """

        refactor_words = (
            "refactor",
            "optimize",
            "optimization",
            "simplify",
            "clean up",
            "clean-up",
            "shorter",
            "cleaner",
            "simpler",
            "efficient",
            "performance",
        )

        if any(word in text for word in refactor_words):
            # Avoid classifying completely unrelated sentences
            # containing "performance", etc.
            code_context = (
                "code" in text
                or "function" in text
                or "program" in text
                or "class" in text
                or "script" in text
            )

            if code_context:
                return True

        # Natural-language patterns.
        flexible_patterns = (
            r"\bmake\s+(?:this|the|my)\s+code\s+(?:shorter|cleaner|simpler)\b",
            r"\bmake\s+(?:this|the|my)\s+(?:code|function|program)\s+\w+er\b",
            r"\breduce\s+(?:the\s+)?(?:code|function|program)\b",
            r"\bremove\s+(?:unnecessary|unused|duplicate)\s+(?:code|lines|logic)\b",
        )

        return any(
            re.search(pattern, text)
            for pattern in flexible_patterns
        )

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        code_markers = (
            "```",
            "def ",
            "class ",
            "import ",
            "from ",
            "function ",
            "const ",
            "let ",
            "var ",
            "#include",
            "public class ",
            "package main",
            "fn main",
            "<?php",
            "select ",
            "insert ",
            "update ",
            "delete ",
        )

        return any(marker in text for marker in code_markers)
