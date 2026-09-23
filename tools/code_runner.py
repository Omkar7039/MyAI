import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tools.runners.base import ExecutionResult


class PythonCodeRunner:
    """
    Execute Python code in an isolated temporary directory.

    Initial execution policy:
    - Python only
    - 5 second timeout
    - no shell execution
    - temporary source file
    """

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def run(self, code: str) -> ExecutionResult:
        start = time.perf_counter()

        if not code.strip():
            return ExecutionResult(
                language="python",
                success=False,
                exit_code=-1,
                stdout="",
                stderr="No code supplied.",
                timed_out=False,
                execution_time=(
                    time.perf_counter() - start
                ),
            )

        with tempfile.TemporaryDirectory(
            prefix="myai_run_"
        ) as tmp_dir:
            script_path = Path(tmp_dir) / "main.py"

            script_path.write_text(
                code,
                encoding="utf-8",
            )

            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        str(script_path),
                    ],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    shell=False,
                )

                elapsed = time.perf_counter() - start

                return ExecutionResult(
                    language="python",
                    success=process.returncode == 0,
                    exit_code=process.returncode,
                    stdout=process.stdout,
                    stderr=process.stderr,
                    timed_out=False,
                    execution_time=elapsed,
                )

            except subprocess.TimeoutExpired as exc:
                elapsed = time.perf_counter() - start

                stdout = exc.stdout or ""
                stderr = exc.stderr or ""

                if isinstance(stdout, bytes):
                    stdout = stdout.decode(
                        "utf-8",
                        errors="replace",
                    )

                if isinstance(stderr, bytes):
                    stderr = stderr.decode(
                        "utf-8",
                        errors="replace",
                    )

                return ExecutionResult(
                    language="python",
                    success=False,
                    exit_code=-1,
                    stdout=stdout,
                    stderr=(
                        f"Execution timed out after "
                        f"{self.timeout} seconds.\n"
                        f"{stderr}"
                    ),
                    timed_out=True,
                    execution_time=elapsed,
                )
