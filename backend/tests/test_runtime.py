import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _get_run_pipelet():
    from backend.app.pipelets.runtime import run_pipelet as _run_pipelet

    return _run_pipelet


run_pipelet = _get_run_pipelet()


def test_success_return_value():
    code = """
def run(message, context):
    return {"x": message.get("a", 0) + 1}
"""
    result, debug, error = run_pipelet(code, {"a": 1}, {})
    assert result == {"x": 2}
    assert debug == ""
    assert error is None


def test_syntax_error():
    code = """
def run(message, context)
    return 42
"""
    result, debug, error = run_pipelet(code, {}, {})
    assert result is None
    assert error is not None
    assert error["type"] in {"SyntaxError", "Exception"}
    assert "SyntaxError" in debug


def test_timeout():
    code = """
import time

def run(message, context):
    time.sleep(5)
"""
    result, debug, error = run_pipelet(code, {}, {}, timeout=1.0)
    assert result is None
    assert error is not None
    assert error["type"] == "Timeout"
    assert "Execution exceeded" in error["message"]

