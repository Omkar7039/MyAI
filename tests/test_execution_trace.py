from tools.execution_trace import (
    ToolExecutionTrace,
    ToolExecutionTracer,
)


def test_record_trace():
    tracer = ToolExecutionTracer()

    trace = tracer.record(
        tool_name="read_file",
        success=True,
        duration_ms=12.5,
    )

    assert trace == ToolExecutionTrace(
        tool_name="read_file",
        success=True,
        duration_ms=12.5,
        error=None,
    )


def test_traces_are_returned_as_tuple():
    tracer = ToolExecutionTracer()

    tracer.record(
        tool_name="read_file",
        success=True,
        duration_ms=1.0,
    )
    tracer.record(
        tool_name="write_file",
        success=False,
        duration_ms=2.0,
        error="permission denied",
    )

    traces = tracer.traces()

    assert isinstance(traces, tuple)
    assert len(traces) == 2
    assert traces[0].tool_name == "read_file"
    assert traces[1].error == "permission denied"


def test_clear_removes_traces():
    tracer = ToolExecutionTracer()

    tracer.record(
        tool_name="read_file",
        success=True,
        duration_ms=1.0,
    )

    tracer.clear()

    assert tracer.traces() == ()


def test_time_returns_monotonic_timer_value():
    tracer = ToolExecutionTracer()

    start = tracer.time()
    end = tracer.time()

    assert end >= start
