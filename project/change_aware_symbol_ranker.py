from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeAwareSymbolEvidence:
    symbol: object
    score: int
    reasons: tuple[str, ...]


class ChangeAwareSymbolRanker:
    def rank(self, symbols, request: str, changed_files=()):
        changed = {str(path) for path in changed_files}
        request_lower = request.lower()
        ranked = []

        for symbol in symbols:
            name = (getattr(symbol, 'name', '') or '').lower()
            parent = (getattr(symbol, 'parent', '') or '').lower()
            file_path = str(getattr(symbol, 'file', '') or '')
            file_lower = file_path.lower()

            score = 0
            reasons = []

            qualified = f'{parent}.{name}' if parent else name

            if qualified and qualified in request_lower:
                score += 100
                reasons.append('exact qualified symbol')
            elif name and name in request_lower:
                score += 50
                reasons.append('exact symbol')

            if parent and parent in request_lower:
                score += 30
                reasons.append('exact parent class')

            if file_path in changed or file_lower in changed:
                score += 100
                reasons.append('recently changed file')

            for word in self._words(request_lower):
                if word == name:
                    score += 20
                    reasons.append(f'name:{word}')
                elif word in name:
                    score += 10
                    reasons.append(f'name-part:{word}')

                if word == parent:
                    score += 15
                    reasons.append(f'class:{word}')

                if word in file_lower:
                    score += 5
                    reasons.append(f'file:{word}')

            if score > 0:
                ranked.append(
                    ChangeAwareSymbolEvidence(
                        symbol=symbol,
                        score=score,
                        reasons=tuple(reasons),
                    )
                )

        ranked.sort(
            key=lambda item: (
                -item.score,
                str(getattr(item.symbol, 'file', '')),
                int(getattr(item.symbol, 'line', 0)),
                str(getattr(item.symbol, 'name', '')),
            )
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
