from dataclasses import dataclass


@dataclass
class RankedEvidence:
    item: object
    score: int
    reasons: list[str]


class ContextRanker:
    """
    Deterministic ranking for project evidence.

    This class does not use the language model.
    """

    def rank_symbols(self, symbols, request: str):
        request_lower = request.lower()
        ranked = []

        for symbol in symbols:
            score = 0
            reasons = []

            name = (getattr(symbol, "name", "") or "").lower()
            parent = (getattr(symbol, "parent", "") or "").lower()
            file_path = (getattr(symbol, "file", "") or "").lower()

            qualified = (
                f"{parent}.{name}"
                if parent
                else name
            )

            qualified = qualified.lower()

            # Exact qualified symbol match.
            if qualified and qualified in request_lower:
                score += 100
                reasons.append("exact qualified symbol")

            # Exact class name.
            if parent and parent in request_lower:
                score += 60
                reasons.append("exact parent class")

            # Exact symbol name.
            if name and name in request_lower:
                score += 50
                reasons.append("exact symbol")

            # Individual request terms.
            for word in self._words(request):
                if word == name:
                    score += 25
                    reasons.append(f"name:{word}")
                elif word in name:
                    score += 12
                    reasons.append(f"name-part:{word}")

                if word == parent:
                    score += 20
                    reasons.append(f"class:{word}")

                if word in file_path:
                    score += 6
                    reasons.append(f"file:{word}")

            # Prefer actual execution-flow methods.
            if name == "handle" and parent == "orchestrator":
                score += 80
                reasons.append("orchestration entry point")

            if name == "build_request" and parent == "orchestrator":
                score += 65
                reasons.append("request construction")

            if name == "analyze" and parent == "debugagent":
                score += 75
                reasons.append("debug execution")

            if name == "repair_and_verify" and parent == "repairagent":
                score += 70
                reasons.append("repair execution")

            if name == "run_tests" and parent == "repairagent":
                score += 45
                reasons.append("repair test execution")

            # Constructors and internal helpers are lower priority.
            if name == "__init__":
                score -= 50

            if name in {
                "_needs_semantic_repair",
                "extract_code",
                "detect_language",
                "_choose_model",
            }:
                score -= 20

            if name == "request":
                score -= 80

            if score > 0:
                ranked.append(
                    RankedEvidence(
                        item=symbol,
                        score=score,
                        reasons=reasons,
                    )
                )

        ranked.sort(
            key=lambda item: (
                -item.score,
                getattr(item.item, "file", ""),
                getattr(item.item, "line", 0),
            )
        )

        return ranked

    def rank_files(self, files, request: str):
        request_lower = request.lower()
        ranked = []

        for file_path in files:
            path = str(file_path)
            path_lower = path.lower()

            score = 0
            reasons = []

            for word in self._words(request):
                if word in path_lower:
                    score += 10
                    reasons.append(f"file:{word}")

            if "orchestrator" in path_lower:
                score += 5

            if "debugging" in path_lower:
                score += 5

            if "repair" in path_lower:
                score += 5

            if "verification" in path_lower:
                score += 2

            ranked.append(
                RankedEvidence(
                    item=file_path,
                    score=score,
                    reasons=reasons,
                )
            )

        ranked.sort(
            key=lambda item: (
                -item.score,
                str(item.item),
            )
        )

        return ranked

    def _words(self, request):
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "from",
            "for",
            "with",
            "this",
            "that",
            "how",
            "what",
            "why",
            "give",
            "only",
            "facts",
            "verified",
        }

        words = []

        for raw in request.lower().replace("_", " ").split():
            word = raw.strip(".,:;!?()[]{}\"'")

            if len(word) < 3:
                continue

            if word in stopwords:
                continue

            words.append(word)

        return words
