from agents.debug_investigation import DebugEvidence
from agents.debugging import DebugAgent


class FakeModel:
    def __init__(self):
        self.prompts = []

    def ask(self, messages, max_tokens=512):
        self.prompts.append(messages)
        return "Root cause identified. Smallest correct fix is available."


class FakeInvestigator:
    def __init__(self, evidence):
        self.evidence = evidence

    def investigate(self, problem, code, error=None, language=None):
        return self.evidence


def make_agent(evidence):
    agent = DebugAgent.__new__(DebugAgent)
    agent.model = FakeModel()
    agent.investigator = FakeInvestigator(evidence)
    return agent


def test_debug_agent_uses_investigator_evidence():
    evidence = DebugEvidence(
        problem="Fix missing variable",
        language="python",
        error="NameError",
        static_analysis="Static analysis: undefined name detected.",
        runtime={
            "language": "python",
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "NameError: missing",
            "timed_out": False,
        },
    )

    agent = make_agent(evidence)

    result = agent.analyze(
        problem="Fix missing variable",
        code="print(missing)",
        error="NameError",
        language="python",
        auto_repair=False,
    )

    prompt = agent.model.prompts[0][0]["content"]

    assert result
    assert "Static analysis: undefined name detected." in prompt
    assert "NameError: missing" in prompt
    assert "Fix missing variable" in prompt


def test_debug_agent_preserves_successful_runtime_path():
    evidence = DebugEvidence(
        problem="Run program",
        language="python",
        error=None,
        static_analysis="Static analysis: clean.",
        runtime={
            "language": "python",
            "success": True,
            "exit_code": 0,
            "stdout": "42",
            "stderr": "",
            "timed_out": False,
        },
    )

    agent = make_agent(evidence)

    result = agent.analyze(
        problem="Run program",
        code="print(42)",
        language="python",
        auto_repair=False,
    )

    assert "=== RUNTIME VERIFICATION ===" in result
    assert "python execution completed successfully." in result
