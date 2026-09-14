import re


class LanguageDetector:
    LANGUAGE_ALIASES = {
        "python": "python",
        "py": "python",
        "javascript": "javascript",
        "js": "javascript",
        "node": "javascript",
        "nodejs": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "java": "java",
        "c++": "cpp",
        "cpp": "cpp",
        "c": "c",
        "c#": "csharp",
        "csharp": "csharp",
        "go": "go",
        "golang": "go",
        "rust": "rust",
        "php": "php",
        "ruby": "ruby",
        "bash": "bash",
        "shell": "bash",
        "sql": "sql",
    }

    def detect(self, text: str) -> str:
        if not text:
            return "unknown"

        lowered = text.lower()

        # ---------------------------------------------------------
        # 1. Explicit language mention has highest priority.
        # ---------------------------------------------------------
        explicit_patterns = [
            (r"\bpython(?:\s+code|\s+program|\s+script)?\b", "python"),
            (r"\bjavascript(?:\s+code|\s+program|\s+script)?\b", "javascript"),
            (r"\bnode\.?js\b", "javascript"),
            (r"\btypescript(?:\s+code|\s+program|\s+script)?\b", "typescript"),
            (r"\bjava(?:\s+code|\s+program|\s+source)?\b", "java"),
            (r"\bc\+\+\b", "cpp"),
            (r"\bc#\b", "csharp"),
            (r"\bgolang\b", "go"),
            (r"\brust\b", "rust"),
            (r"\bphp\b", "php"),
            (r"\bruby\b", "ruby"),
            (r"\bbash\b", "bash"),
            (r"\bshell\s+script\b", "bash"),
            (r"\bsql\b", "sql"),
        ]

        for pattern, language in explicit_patterns:
            if re.search(pattern, lowered):
                return language

        # ---------------------------------------------------------
        # 2. Markdown fenced code.
        # ---------------------------------------------------------
        fence_match = re.search(
            r"```([a-zA-Z0-9_+#.-]+)",
            text,
            re.IGNORECASE,
        )

        if fence_match:
            token = fence_match.group(1).lower()

            if token in self.LANGUAGE_ALIASES:
                return self.LANGUAGE_ALIASES[token]

        # ---------------------------------------------------------
        # 3. Python syntax heuristics.
        # ---------------------------------------------------------
        python_signals = [
            r"\bdef\s+\w+\s*\(",
            r"\bimport\s+\w+",
            r"\bfrom\s+\w+\s+import\b",
            r"\bprint\s*\(",
            r"\bNone\b",
            r"\bTrue\b",
            r"\bFalse\b",
            r"\belif\b",
        ]

        python_score = sum(
            bool(re.search(pattern, text))
            for pattern in python_signals
        )

        # ---------------------------------------------------------
        # 4. JavaScript / Node syntax heuristics.
        # ---------------------------------------------------------
        javascript_signals = [
            r"\bfunction\s+\w+\s*\(",
            r"\bconsole\.(log|error|warn)\s*\(",
            r"\b(let|const|var)\s+\w+",
            r"\bundefined\b",
            r"\bNaN\b",
            r"=>",
            r"\brequire\s*\(",
            r"\bmodule\.exports\b",
        ]

        javascript_score = sum(
            bool(re.search(pattern, text))
            for pattern in javascript_signals
        )

        # ---------------------------------------------------------
        # 5. Other language heuristics.
        # ---------------------------------------------------------
        if python_score > javascript_score and python_score >= 1:
            return "python"

        if javascript_score > python_score and javascript_score >= 1:
            return "javascript"

        if re.search(
            r"#include\s*[<\"]",
            text,
        ):
            if re.search(
                r"\b(std::|cout\s*<<|cin\s*>>|using\s+namespace\s+std)",
                text,
            ):
                return "cpp"

            return "c"

        if re.search(
            r"\b(public\s+static\s+void\s+main|System\.out\.println)",
            text,
        ):
            return "java"

        if re.search(
            r"\bpackage\s+main\b|\bfmt\.Print",
            text,
        ):
            return "go"

        if re.search(
            r"\bfn\s+main\s*\(|\blet\s+mut\s+\w+",
            text,
        ):
            return "rust"

        if re.search(
            r"<\?php|\becho\s+",
            text,
        ):
            return "php"

        if re.search(
            r"\bSELECT\b.+\bFROM\b",
            text,
            re.IGNORECASE | re.DOTALL,
        ):
            return "sql"

        return "unknown"
