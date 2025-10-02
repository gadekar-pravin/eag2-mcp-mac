"""Utilities for executing AppleScript files via ``osascript``."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


class AppleScriptError(RuntimeError):
    """Raised when an AppleScript invocation fails."""


def run_applescript_file(path: str | Path, args: Sequence[str] | None = None, timeout: int = 15) -> str:
    """Run an AppleScript file using ``osascript``.

    Parameters
    ----------
    path:
        Path to the AppleScript file.
    args:
        Optional iterable of string arguments passed to the script.
    timeout:
        Timeout in seconds before the subprocess is terminated.

    Returns
    -------
    str
        The stdout emitted by the AppleScript, stripped of trailing whitespace.

    Raises
    ------
    FileNotFoundError
        If the AppleScript file does not exist.
    AppleScriptError
        If the script exits with a non-zero status or times out.
    """

    script_path = Path(path)
    if not script_path.exists():
        raise FileNotFoundError(f"AppleScript file not found: {script_path}")

    cmd = ["osascript", str(script_path)]
    if args:
        cmd.extend(str(arg) for arg in args)

    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.CalledProcessError as exc:
        message = exc.output.decode("utf-8", errors="ignore").strip()
        raise AppleScriptError(message or f"AppleScript failed: {script_path}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AppleScriptError(f"AppleScript timed out after {timeout}s: {script_path}") from exc

    return output.decode("utf-8", errors="ignore").strip()
