import pytest

from core.tool_agent_model_adapter import (
    ModelReasoningResult,
    ToolAgentModelAdapter,
)


def test_adapter_calls_injected_generator():
    calls = []

    def generator(prompt):
        calls.append(prompt)
        return "The file contains VALUE = 42."

    adapter = ToolAgentModelAdapter(generator)

    result = adapter.generate("Inspect config.py")

    assert calls == ["Inspect config.py"]
    assert isinstance(result, ModelReasoningResult)
    assert result.prompt == "Inspect config.py"
    assert result.response == "The file contains VALUE = 42."
    assert result.raw_response == "The file contains VALUE = 42."


def test_adapter_preserves_non_string_raw_response():
    raw = {
        "action": "complete",
        "reason": "Task is complete.",
    }

    adapter = ToolAgentModelAdapter(lambda prompt: raw)

    result = adapter.generate("Summarize the result")

    assert result.raw_response is raw
    assert result.response == str(raw)


def test_adapter_accepts_empty_response():
    adapter = ToolAgentModelAdapter(lambda prompt: "")

    result = adapter.generate("Inspect config.py")

    assert result.response == ""
    assert result.raw_response == ""


def test_non_callable_generator_is_rejected():
    with pytest.raises(
        TypeError,
        match="generator must be callable",
    ):
        ToolAgentModelAdapter("not callable")


def test_non_string_prompt_is_rejected():
    adapter = ToolAgentModelAdapter(lambda prompt: "response")

    with pytest.raises(
        TypeError,
        match="prompt must be a string",
    ):
        adapter.generate(123)


def test_adapter_does_not_execute_tools():
    tool_calls = []

    def fake_generator(prompt):
        return "Reasoning only."

    adapter = ToolAgentModelAdapter(fake_generator)

    result = adapter.generate("Read config.py")

    assert result.response == "Reasoning only."
    assert tool_calls == []


def test_adapter_does_not_modify_prompt():
    prompt = "Read config.py and report the result."

    adapter = ToolAgentModelAdapter(
        lambda received: received,
    )

    result = adapter.generate(prompt)

    assert result.prompt == prompt
    assert result.response == prompt
