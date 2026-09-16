from __future__ import annotations

from core.orchestrator import Orchestrator
from experience.learning_signal import LearningSignalCollector


class FakeDebugAgent:
    def __init__(self):
        self.calls = []

    def analyze(
        self,
        *,
        problem,
        code,
        language,
        auto_repair,
        repair_strategy="standard",
    ):
        self.calls.append(
            {
                "problem": problem,
                "code": code,
                "language": language,
                "auto_repair": auto_repair,
                "repair_strategy": repair_strategy,
            }
        )
        return "debug-result"


def make_signals(strategy="property", score=100.0):
    collector = LearningSignalCollector()

    return [
        collector.repair_success(
            f"task-{index}",
            strategy=strategy,
            score=score,
        )
        for index in range(5)
    ]


def make_orchestrator():
    orchestrator = Orchestrator.__new__(Orchestrator)

    from experience.learning_orchestrator import UnifiedLearningRouter
    from experience.governed_strategy_router import GovernedStrategyRouter

    orchestrator.learning_router = UnifiedLearningRouter()
    orchestrator.governed_learning_router = GovernedStrategyRouter()
    orchestrator.debug_agent = FakeDebugAgent()

    orchestrator.build_request = lambda user_input: type(
        "Request",
        (),
        {
            "raw_text": user_input,
            "intent": "debug",
            "confidence": 1.0,
            "code": "def add(a, b):\n    return a - b\n",
            "language": "python",
            "difficulty": "easy",
            "difficulty_score": 1,
            "difficulty_reasons": [],
        },
    )()

    orchestrator._choose_model = lambda request: type(
        "ModelProfile",
        (),
        {"name": "test"},
    )()

    return orchestrator


def test_governed_strategy_reaches_debug_agent():
    orchestrator = make_orchestrator()

    result = orchestrator.handle(
        "debug this python code",
        learning_signals=make_signals(),
        utility_by_strategy={"property": 100.0},
        baseline_score_by_strategy={"property": 70.0},
    )

    assert result == "debug-result"
    assert len(orchestrator.debug_agent.calls) == 1
    assert (
        orchestrator.debug_agent.calls[0]["repair_strategy"]
        == "property"
    )


def test_without_governance_learning_strategy_still_reaches_debug_agent():
    orchestrator = make_orchestrator()

    result = orchestrator.handle(
        "debug this python code",
        learning_signals=[],
    )

    assert result == "debug-result"
    assert (
        orchestrator.debug_agent.calls[0]["repair_strategy"]
        == "standard"
    )


def test_governance_rejection_preserves_safe_learning_route():
    orchestrator = make_orchestrator()

    result = orchestrator.handle(
        "debug this python code",
        learning_signals=make_signals(
            strategy="property",
            score=40.0,
        ),
        utility_by_strategy={"property": 40.0},
        baseline_score_by_strategy={"property": 100.0},
    )

    assert result == "debug-result"
    assert (
        orchestrator.debug_agent.calls[0]["repair_strategy"]
        == "property"
    )


def test_debug_agent_accepts_repair_strategy_without_breaking_old_api():
    calls = []

    class FakeRepairAgent:
        def repair_and_verify(
            self,
            *,
            code,
            problem,
            strategy="standard",
        ):
            calls.append(strategy)
            return {
                "success": False,
                "reason": "test",
                "attempts": [],
            }

    from agents.debugging import DebugAgent

    agent = DebugAgent.__new__(DebugAgent)
    agent.repair_agent = FakeRepairAgent()

    class FakeInvestigator:
        def investigate(self, **kwargs):
            return type(
                "Investigation",
                (),
                {
                    "static_analysis": "test",
                    "runtime": {
                        "language": "python",
                        "success": False,
                        "exit_code": 1,
                        "timed_out": False,
                        "stdout": "",
                        "stderr": "failure",
                    },
                },
            )()

    agent.investigator = FakeInvestigator()

    agent.model = type(
        "Model",
        (),
        {
            "ask": lambda self, messages, max_tokens: "diagnosis",
        },
    )()

    result = agent.analyze(
        problem="debug code",
        code="def f():\n    return 1\n",
        language="python",
        auto_repair=True,
        repair_strategy="property",
    )

    assert "AUTOMATIC REPAIR" in result
    assert calls == ["property"]
