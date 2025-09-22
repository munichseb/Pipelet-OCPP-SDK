"""Tests for executing workflows via the runtime runner."""
from __future__ import annotations

import json
import pathlib
import sys
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_chain_graph(codes: list[str]) -> dict[str, object]:
    nodes: dict[str, object] = {}
    for index, code in enumerate(codes, start=1):
        node_id = str(index)
        outputs: dict[str, object] = {}
        if index < len(codes):
            outputs = {
                "out": {
                    "connections": [
                        {"node": index + 1},
                    ]
                }
            }
        nodes[node_id] = {
            "id": index,
            "data": {
                "code": code,
                "pipelet": {"name": f"Node {index}"},
            },
            "outputs": outputs,
        }
    return {"nodes": nodes}


def _prepare_workflow(graph: dict[str, object], **kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(
        id=kwargs.get("id", 1),
        name=kwargs.get("name", "Workflow"),
        event=kwargs.get("event", "StartTransaction"),
        graph_json=json.dumps(graph),
    )


def _patch_workflow_query(monkeypatch: pytest.MonkeyPatch, workflow: SimpleNamespace) -> None:
    from backend.app.workflow import runner

    class _DummyQuery:
        def filter(self, *args: object, **kwargs: object) -> _DummyQuery:
            return self

        def first(self) -> SimpleNamespace:
            return workflow

    class _DummyWorkflow:
        event = object()
        query = _DummyQuery()

    monkeypatch.setattr(runner, "Workflow", _DummyWorkflow)


def _capture_logs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    from backend.app.workflow import runner

    captured: list[tuple[str, str]] = []

    def _fake_log(source: str, message: str) -> None:
        captured.append((source, message))

    monkeypatch.setattr(runner, "_persist_run_log", _fake_log)
    return captured


def test_workflow_chain_execution(monkeypatch: pytest.MonkeyPatch):
    from backend.app.workflow.runner import run_workflow_for_event

    code_a = """
from copy import deepcopy

def run(message, context):
    data = deepcopy(message)
    data[\"a\"] = 1
    return data
"""
    code_b = """
from copy import deepcopy

def run(message, context):
    data = deepcopy(message)
    data[\"b\"] = data.get(\"a\", 0) + 1
    return data
"""
    graph = _make_chain_graph([code_a, code_b])
    workflow = _prepare_workflow(graph, name="Chain", event="StartTransaction")
    _patch_workflow_query(monkeypatch, workflow)
    _capture_logs(monkeypatch)

    result = run_workflow_for_event("StartTransaction", {"x": 0}, {"cp_id": "CP_1"})

    assert result == {"x": 0, "a": 1, "b": 2}


def test_workflow_continues_after_error(monkeypatch: pytest.MonkeyPatch):
    from backend.app.workflow.runner import run_workflow_for_event

    code_error = """
def run(message, context):
    raise ValueError(\"boom\")
"""
    code_after = """
from copy import deepcopy

def run(message, context):
    data = deepcopy(message)
    data[\"after_error\"] = True
    return data
"""
    graph = _make_chain_graph([code_error, code_after])
    workflow = _prepare_workflow(graph, name="ErrorChain", event="Authorize")
    _patch_workflow_query(monkeypatch, workflow)
    logs = _capture_logs(monkeypatch)

    result = run_workflow_for_event("Authorize", {"start": True}, {"cp_id": "CP_1"})

    assert result == {"start": True, "after_error": True}
    error_log = next(
        json.loads(message)
        for source, message in logs
        if source == "pipelet" and json.loads(message)["event"] == "Authorize"
    )
    assert error_log["error"]["type"] == "Exception"


def test_workflow_continues_after_timeout(monkeypatch: pytest.MonkeyPatch):
    from backend.app.workflow.runner import run_workflow_for_event

    code_timeout = """
import time

def run(message, context):
    time.sleep(5)
"""
    code_after = """
from copy import deepcopy

def run(message, context):
    data = deepcopy(message)
    data[\"timeout\"] = False
    return data
"""
    graph = _make_chain_graph([code_timeout, code_after])
    workflow = _prepare_workflow(graph, name="TimeoutChain", event="StopTransaction")
    _patch_workflow_query(monkeypatch, workflow)
    logs = _capture_logs(monkeypatch)

    result = run_workflow_for_event(
        "StopTransaction",
        {"start": False},
        {"cp_id": "CP_1"},
        timeout_per_node=0.2,
    )

    assert result == {"start": False, "timeout": False}
    timeout_log = next(
        json.loads(message)
        for source, message in logs
        if source == "pipelet" and json.loads(message)["event"] == "StopTransaction"
    )
    assert timeout_log["error"]["type"] == "Timeout"
