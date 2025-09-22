"""Workflow runtime for executing pipelet chains based on events."""
from __future__ import annotations

import heapq
import json
from typing import Any

from ..extensions import db
from ..models.logs import RunLog
from ..models.workflow import Workflow
from ..pipelets.runtime import run_pipelet


class WorkflowExecutionError(Exception):
    """Raised when a workflow cannot be executed."""


def _persist_run_log(source: str, message: str) -> None:
    """Persist a run log entry and suppress database errors."""

    if not message:
        return

    try:
        entry = RunLog(source=source, message=message)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _extract_nodes(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for key, node in nodes.items():
        if not isinstance(node, dict):
            continue
        identifier = node.get("id", key)
        node_id = str(identifier)
        normalized[node_id] = node
    return normalized


def _topological_order(nodes: dict[str, dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    adjacency: dict[str, set[str]] = {}
    indegree: dict[str, int] = {}

    for node_id, node in nodes.items():
        adjacency[node_id] = set()
        indegree.setdefault(node_id, 0)

        outputs = node.get("outputs")
        if not isinstance(outputs, dict):
            continue

        for output in outputs.values():
            if not isinstance(output, dict):
                continue
            connections = output.get("connections")
            if not isinstance(connections, list):
                continue
            for connection in connections:
                if not isinstance(connection, dict):
                    continue
                target = connection.get("node")
                if target is None:
                    continue
                target_id = str(target)
                if target_id not in nodes:
                    continue
                adjacency[node_id].add(target_id)
                indegree[target_id] = indegree.get(target_id, 0) + 1

    heap: list[str] = []
    for node_id, degree in indegree.items():
        if degree == 0:
            heapq.heappush(heap, node_id)

    ordered: list[str] = []
    while heap:
        node_id = heapq.heappop(heap)
        ordered.append(node_id)
        for neighbour in sorted(adjacency.get(node_id, set())):
            indegree[neighbour] -= 1
            if indegree[neighbour] == 0:
                heapq.heappush(heap, neighbour)

    if len(ordered) != len(nodes):
        raise WorkflowExecutionError("cycle detected in workflow graph")

    return [(node_id, nodes[node_id]) for node_id in ordered]


def _node_pipelet_name(node: dict[str, Any]) -> str | None:
    data = node.get("data")
    if not isinstance(data, dict):
        return None

    pipelet_info = data.get("pipelet")
    if isinstance(pipelet_info, dict):
        name = pipelet_info.get("name")
        if isinstance(name, str):
            return name

    name = data.get("name")
    if isinstance(name, str):
        return name

    return node.get("name") if isinstance(node.get("name"), str) else None


def _node_code(node: dict[str, Any]) -> str | None:
    data = node.get("data")
    if isinstance(data, dict):
        code = data.get("code")
        if isinstance(code, str):
            return code
    return None


def run_workflow_for_event(
    event: str,
    message: dict[str, Any] | None,
    context: dict[str, Any] | None,
    timeout_per_node: float = 1.5,
) -> dict[str, Any] | None:
    """Execute the workflow bound to the given event."""

    workflow = Workflow.query.filter(Workflow.event == event).first()
    if workflow is None:
        return message

    try:
        graph = json.loads(workflow.graph_json or "{}")
    except (TypeError, ValueError):
        _persist_run_log(
            "cs",
            f"workflow {workflow.id} has invalid graph definition; skipping execution",
        )
        return message

    nodes = _extract_nodes(graph)
    if not nodes:
        _persist_run_log(
            "cs",
            f"workflow {workflow.name} executed for event {event} with 0 nodes",
        )
        return message

    try:
        ordered_nodes = _topological_order(nodes)
    except WorkflowExecutionError as exc:
        _persist_run_log(
            "cs",
            f"workflow {workflow.name} execution aborted: {exc}",
        )
        return message

    base_message = message if isinstance(message, dict) else {}
    current_message: dict[str, Any] = dict(base_message)
    current_context: dict[str, Any] = dict(context or {})

    for node_id, node in ordered_nodes:
        code = _node_code(node)
        pipelet_name = _node_pipelet_name(node)
        debug_output = ""
        error_payload: dict[str, Any] | None = None

        if code is None:
            error_payload = {
                "type": "ConfigurationError",
                "message": "Pipelet code missing",
            }
            result = None
        else:
            result, debug_output, error_payload = run_pipelet(
                code,
                current_message,
                current_context,
                timeout=timeout_per_node,
            )

        log_payload = {
            "event": event,
            "workflow_id": workflow.id,
            "workflow": workflow.name,
            "node": node_id,
            "pipelet": pipelet_name,
            "debug": debug_output,
            "error": error_payload,
        }
        _persist_run_log("pipelet", json.dumps(log_payload))

        if isinstance(result, dict):
            current_message = result

    _persist_run_log(
        "cs",
        f"workflow {workflow.name} executed for event {event}",
    )

    return current_message
