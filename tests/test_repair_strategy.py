from agents.repair import RepairAgent
from agents.repair_strategy import (
    RepairStrategyDecision,
    RepairStrategyExecutor,
)


def test_standard_strategy_is_applied_without_fallback():
    executor = RepairStrategyExecutor()

    decision = executor.resolve("standard")

    assert isinstance(decision, RepairStrategyDecision)
    assert decision.requested == "standard"
    assert decision.applied == "standard"
    assert decision.fallback is False
    assert "standard" in decision.reason


def test_strategy_name_is_normalized():
    executor = RepairStrategyExecutor()

    decision = executor.resolve("  STANDARD  ")

    assert decision.requested == "standard"
    assert decision.applied == "standard"
    assert decision.fallback is False


def test_unsupported_strategy_safely_falls_back_to_standard():
    executor = RepairStrategyExecutor()

    decision = executor.resolve("mutation")

    assert decision.requested == "mutation"
    assert decision.applied == "standard"
    assert decision.fallback is True
    assert "not implemented" in decision.reason


def test_empty_strategy_is_rejected():
    executor = RepairStrategyExecutor()

    try:
        executor.resolve("   ")
    except ValueError as exc:
        assert str(exc) == "strategy must not be empty"
    else:
        raise AssertionError("expected ValueError")


class _TestGenerator:
    def generate_python_tests(self, *, code, problem):
        return "def test_example():\n    assert True\n"


class _PropertyEngine:
    def infer_properties(self, *, source_code, problem):
        return []


def test_repair_agent_uses_standard_strategy_by_default(monkeypatch):
    agent = RepairAgent.__new__(RepairAgent)
    agent.strategy_executor = RepairStrategyExecutor()
    agent.test_generator = _TestGenerator()
    agent.property_engine = _PropertyEngine()

    monkeypatch.setattr(
        agent,
        "run_tests",
        lambda code, tests: {
            "success": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        },
    )

    monkeypatch.setattr(
        agent,
        "strengthen_tests",
        lambda *, code, tests: {
            "success": True,
            "tests": tests,
            "mutation": {"score": 1.0},
        },
    )

    monkeypatch.setattr(
        agent,
        "_acceptance_check",
        lambda *, code, problem, tests: {
            "accepted": True,
            "tests_passed": True,
            "mutation_passed": True,
            "property_passed": False,
            "property_available": False,
            "mutation": {"score": 1.0},
            "properties": None,
        },
    )

    recorded = []
    monkeypatch.setattr(
        agent,
        "_record_experience",
        lambda problem, result: recorded.append(result),
    )

    result = agent.repair_and_verify(
        code="def example():\n    return True\n",
        problem="keep example working",
    )

    assert result["success"] is True
    assert result["strategy"] == "standard"
    assert result["requested_strategy"] == "standard"
    assert result["strategy_fallback"] is False
    assert recorded[0]["strategy"] == "standard"


def test_repair_agent_falls_back_for_unsupported_strategy(monkeypatch):
    agent = RepairAgent.__new__(RepairAgent)
    agent.strategy_executor = RepairStrategyExecutor()
    agent.test_generator = _TestGenerator()
    agent.property_engine = _PropertyEngine()

    monkeypatch.setattr(
        agent,
        "run_tests",
        lambda code, tests: {
            "success": True,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        },
    )

    monkeypatch.setattr(
        agent,
        "strengthen_tests",
        lambda *, code, tests: {
            "success": True,
            "tests": tests,
            "mutation": {"score": 1.0},
        },
    )

    monkeypatch.setattr(
        agent,
        "_acceptance_check",
        lambda *, code, problem, tests: {
            "accepted": True,
            "tests_passed": True,
            "mutation_passed": True,
            "property_passed": False,
            "property_available": False,
            "mutation": {"score": 1.0},
            "properties": None,
        },
    )

    monkeypatch.setattr(
        agent,
        "_record_experience",
        lambda problem, result: None,
    )

    result = agent.repair_and_verify(
        code="def example():\n    return True\n",
        problem="keep example working",
        strategy="mutation",
    )

    assert result["success"] is True
    assert result["strategy"] == "standard"
    assert result["requested_strategy"] == "mutation"
    assert result["strategy_fallback"] is True
    assert "not implemented" in result["strategy_reason"]
