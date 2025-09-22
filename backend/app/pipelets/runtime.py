"""Runtime utilities for executing pipelet code in a sandboxed subprocess."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any

from ..utils import security

_PIPELET_WRAPPER_TEMPLATE = """import json, sys\n""" \
    "inp = json.loads(sys.stdin.read() or \"{}\")\n" \
    "message = inp.get(\"message\")\n" \
    "context = inp.get(\"context\", {})\n" \
    "{CODE}\n" \
    "out = run(message, context)\n" \
    "print(json.dumps({\"result\": out}))\n"


ResultType = tuple[Any, str, dict[str, Any] | None]


def _build_wrapper_source(code: str) -> str:
    """Embed user supplied code inside the execution template."""
    return _PIPELET_WRAPPER_TEMPLATE.replace("{CODE}", code)


def _write_wrapper_file(code: str) -> str:
    """Persist the wrapper code to a temporary file and return its path."""
    wrapper_source = _build_wrapper_source(code)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(wrapper_source)
        tmp_file.flush()
        return tmp_file.name


def _collect_error(debug: str, default_type: str = "Exception") -> dict[str, str]:
    error_type = "SyntaxError" if "SyntaxError" in debug else default_type
    message = "Pipelet execution failed"
    if debug:
        last_line = debug.strip().splitlines()[-1]
        if last_line:
            message = last_line
    return {"type": error_type, "message": message}


def run_pipelet(
    code: str,
    message: dict[str, Any],
    context: dict[str, Any] | None,
    timeout: float = 1.5,
) -> ResultType:
    """Execute a pipelet definition in an isolated subprocess."""
    context = context or {}
    wrapper_path = _write_wrapper_file(code)
    debug_output = ""
    try:
        payload = json.dumps({"message": message, "context": context})
        preexec_fn = security.build_preexec_fn()
        completed = subprocess.run(
            [sys.executable, "-I", wrapper_path],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            preexec_fn=preexec_fn,
        )
        debug_output = completed.stderr or ""
        if completed.returncode != 0:
            return None, debug_output, _collect_error(debug_output)

        stdout_text = completed.stdout or ""
        try:
            parsed = json.loads(stdout_text or "{}")
        except json.JSONDecodeError:
            return None, debug_output, {
                "type": "ProtocolError",
                "message": "Invalid JSON output from pipelet",
            }
        return parsed.get("result"), debug_output, None
    except subprocess.TimeoutExpired as exc:
        debug_output = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return None, debug_output, {
            "type": "Timeout",
            "message": f"Execution exceeded {timeout} seconds",
        }
    finally:
        try:
            os.unlink(wrapper_path)
        except OSError:
            pass

