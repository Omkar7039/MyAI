from agents.repair import RepairAgent


class DummyRecorder:
    def __init__(self):
        self.kwargs = None

    def record_repair(self, **kwargs):
        self.kwargs = kwargs


def test_repair_agent_records_provenance():
    agent = RepairAgent.__new__(RepairAgent)
    agent.experience_recorder = DummyRecorder()

    result = {
        "success": True,
        "verified": True,
        "behavior_verified": True,
        "mutation_verified": True,
        "property_available": True,
        "property_verified": True,
        "attempts": [{"attempt": 1}],
    }

    agent._record_experience(
        "The parser validation function rejects valid input.",
        result,
    )

    provenance = agent.experience_recorder.kwargs["provenance"]

    assert provenance.source == "repair"
    assert provenance.workflow == "repair_and_verify"
    assert provenance.verified is True
    assert "regression behavior verified" in provenance.evidence
    assert "mutation verification passed" in provenance.evidence
    assert "property verification passed" in provenance.evidence
