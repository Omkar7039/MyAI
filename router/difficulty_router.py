from dataclasses import dataclass


@dataclass
class DifficultyResult:
    level: str
    score: int
    reasons: list[str]


class DifficultyRouter:
    """
    Estimates task complexity using multiple signals.

    Score:
        0-24   easy
        25-49  medium
        50-74  hard
        75-100 expert
    """

    def analyze(
        self,
        text: str,
        code: str | None = None,
        language: str = "unknown",
    ) -> DifficultyResult:

        value = text.lower()

        score = 0
        reasons: list[str] = []

        # --------------------------------------------------
        # Code size
        # --------------------------------------------------
        if code:
            lines = len(code.splitlines())

            if lines >= 500:
                score += 40
                reasons.append("very large code block")
            elif lines >= 200:
                score += 30
                reasons.append("large code block")
            elif lines >= 100:
                score += 20
                reasons.append("medium-large code block")
            elif lines >= 50:
                score += 12
                reasons.append("medium code block")
            elif lines >= 20:
                score += 6
                reasons.append("non-trivial code size")

        # --------------------------------------------------
        # Multi-concept / advanced engineering signals
        # --------------------------------------------------
        concept_weights = {
            "concurrency": 15,
            "race condition": 20,
            "deadlock": 20,
            "distributed": 15,
            "microservice": 12,
            "production": 12,
            "security": 12,
            "authentication": 8,
            "authorization": 8,
            "memory leak": 15,
            "performance": 10,
            "optimization": 10,
            "database migration": 12,
            "architecture": 12,
            "scalability": 12,
            "multi-thread": 15,
            "multithread": 15,
            "async": 8,
            "race": 10,
            "algorithm": 8,
            "complexity": 6,
            "networking": 8,
            "distributed system": 15,
            "parallel": 10,
        }

        for concept, weight in concept_weights.items():
            if concept in value:
                score += weight
                reasons.append(concept)

        # --------------------------------------------------
        # Task type
        # --------------------------------------------------
        if any(
            word in value
            for word in (
                "debug",
                "debugging",
                "bug",
                "error",
                "exception",
                "crash",
                "traceback",
                "repair",
                "fix",
            )
        ):
            score += 8
            reasons.append("debug/repair task")

        if any(
            word in value
            for word in (
                "review",
                "security review",
                "audit",
            )
        ):
            score += 8
            reasons.append("review/audit")

        if any(
            word in value
            for word in (
                "refactor",
                "optimize",
                "optimization",
                "performance",
                "make it faster",
            )
        ):
            score += 8
            reasons.append("optimization/refactor")

        if any(
            word in value
            for word in (
                "prove",
                "proof",
                "derive",
                "formal",
                "why is this correct",
            )
        ):
            score += 15
            reasons.append("proof/formal reasoning")

        # --------------------------------------------------
        # Project scope
        # --------------------------------------------------
        if any(
            word in value
            for word in (
                "repository",
                "repo",
                "codebase",
                "whole project",
                "entire project",
                "architecture",
            )
        ):
            score += 20
            reasons.append("project-level scope")

        # --------------------------------------------------
        # Language/tooling complexity
        # --------------------------------------------------
        if language in {
            "c",
            "cpp",
            "java",
            "rust",
            "go",
            "csharp",
        }:
            score += 5
            reasons.append(
                f"{language} requires compile/tool verification"
            )

        # --------------------------------------------------
        # Multiple requirements
        # --------------------------------------------------
        requirement_count = value.count(" and ")

        if requirement_count >= 3:
            score += 10
            reasons.append("many requirements")
        elif requirement_count >= 1:
            score += 3

        # --------------------------------------------------
        # Clamp
        # --------------------------------------------------
        score = min(score, 100)

        if score >= 75:
            level = "expert"
        elif score >= 50:
            level = "hard"
        elif score >= 25:
            level = "medium"
        else:
            level = "easy"

        return DifficultyResult(
            level=level,
            score=score,
            reasons=reasons,
        )
