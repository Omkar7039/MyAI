from __future__ import annotations

from dataclasses import dataclass

from experience.adaptive_strategy import (
    AdaptiveStrategyRanker,
)
from experience.historical_learning import (
    HistoricalLearningRetriever,
)
from experience.learning_policy import LearningPolicy
from experience.learning_signal import LearningSignal


@dataclass(frozen=True)
class HistoricalLearningInjection:
    signals: tuple[LearningSignal, ...]
    utility_by_strategy: dict[str, float]
    retrieved: int


class HistoricalLearningInjector:
    """
    Retrieve active persisted learning and prepare it for routing.

    Utility is derived from observed signal scores per strategy.
    This component does not perform routing itself.
    """

    def __init__(
        self,
        retriever: HistoricalLearningRetriever,
    ):
        self.retriever = retriever

    def recent(
        self,
        limit: int = 20,
    ) -> HistoricalLearningInjection:
        result = self.retriever.recent(limit)

        return self._build(result.signals)

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> HistoricalLearningInjection:
        result = self.retriever.search(query, limit)

        return self._build(result.signals)

    def _build(
        self,
        signals: tuple[LearningSignal, ...],
    ) -> HistoricalLearningInjection:
        utility_by_strategy: dict[str, float] = {}

        strategies = {
            signal.strategy.strip().lower()
            for signal in signals
            if signal.strategy.strip()
        }

        for strategy in strategies:
            strategy_signals = [
                signal
                for signal in signals
                if signal.strategy.strip().lower() == strategy
            ]

            if not strategy_signals:
                continue

            average_score = sum(
                signal.score
                for signal in strategy_signals
            ) / len(strategy_signals)

            utility_by_strategy[strategy] = average_score

        return HistoricalLearningInjection(
            signals=signals,
            utility_by_strategy=utility_by_strategy,
            retrieved=len(signals),
        )
