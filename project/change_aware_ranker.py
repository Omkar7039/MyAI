from __future__ import annotations

from dataclasses import dataclass

from project.context_ranker import RankedEvidence


@dataclass(frozen=True)
class ChangeAwareEvidence:
    item: object
    score: int
    reasons: tuple[str, ...]


class ChangeAwareRanker:
    def rank(self, files, request: str, changed_files=()):
        changed = {str(path) for path in changed_files}
        request_lower = request.lower()
        ranked = []

        for file_path in files:
            path = str(file_path)
            path_lower = path.lower()
            score = 0
            reasons = []

            if path in changed:
                score += 100
                reasons.append('recently changed')

            for word in self._words(request_lower):
                if word in path_lower:
                    score += 10
                    reasons.append(f'file:{word}')

            ranked.append(
                ChangeAwareEvidence(
                    item=file_path,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        ranked.sort(
            key=lambda item: (-item.score, str(item.item)),
        )
        return ranked

    @staticmethod
    def _words(request: str):
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'to', 'from',
            'for', 'with', 'this', 'that', 'how', 'what',
            'why', 'fix', 'change',
        }

        words = []
        for raw in request.replace('_', ' ').split():
            word = raw.strip('.,:;!?()[]{}\"\'')
            if len(word) >= 3 and word not in stopwords:
                words.append(word)

        return words
