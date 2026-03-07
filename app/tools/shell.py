from __future__ import annotations

import subprocess

from app.schemas.tool_result import ToolResult


def run_command(command: str, timeout_sec: int = 60) -> ToolResult:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        return ToolResult(
            ok=(result.returncode == 0),
            output={
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            },
            error=None if result.returncode == 0 else f"command failed: {result.returncode}",
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, error=f"command timeout after {timeout_sec}s")
    except Exception as e:
        return ToolResult(ok=False, error=str(e))