import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool


class PythonCodeRunner:
    """
    Safely run a Python snippet in a temporary directory.

    Initial version:
    - Python only
    - 5 second timeout
    - no shell execution
    - temporary source file
    """

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def run(self, code: str) -> RunResult:
        if not code.strip():
            return RunResult(
                exit_code=-1,
                stdout="",
                stderr="No code supplied.",
                timed_out=False,
            )

        with tempfile.TemporaryDirectory(prefix="myai_run_") as tmp_dir:
            script_path = Path(tmp_dir) / "main.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                process = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    shell=False,
                )

                return RunResult(
                    exit_code=process.returncode,
                    stdout=process.stdout,
                    stderr=process.stderr,
                    timed_out=False,
                )

            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""

                if isinstance(stdout, bytes):
                    stdout = stdout.decode("utf-8", errors="replace")

                if isinstance(stderr, bytes):
                    stderr = stderr.decode("utf-8", errors="replace")

                return RunResult(
                    exit_code=-1,
                    stdout=stdout,
                    stderr=f"Execution timed out after {self.timeout} seconds.\n{stderr}",
                    timed_out=True,
                )
