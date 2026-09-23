from types import SimpleNamespace

from core.orchestrator import Orchestrator
from core.tool_result_observer import ToolObservation


class FakeObserver:
    def __init__(self):
        self.received = None

    def observe(self, execution_plan):
        self.received = execution_plan
        return ToolObservation(
            tool_name="read_file",
            success=True,
            result="VALUE = 42\n",
            error=None,
            executed=True,
        )


def test_orchestrator_observe_tool_result_delegates_to_observer():
    orchestrator = object.__new__(Orchestrator)

    observer = FakeObserver()
    orchestrator.tool_result_observer = observer

    execution_plan = SimpleNamespace(name="test-plan")

    result = orchestrator.observe_tool_result(execution_plan)

    assert observer.received is execution_plan
    assert isinstance(result, ToolObservation)
    assert result.tool_name == "read_file"
    assert result.success is True
    assert result.result == "VALUE = 42\n"
    assert result.executed is True
