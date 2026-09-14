from dataclasses import dataclass


@dataclass
class ExecutionResult:
    language: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    execution_time: float
