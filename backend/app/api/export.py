"""API endpoints for exporting and importing configuration snapshots."""
from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models.pipelet import Pipelet
from ..models.workflow import Workflow
from ..utils.auth import require_token
from .pipelets import _validate_pipelet_payload
from .workflow import _normalize_event, _normalize_graph

bp = Blueprint("export", __name__)


def _serialize_pipelets(pipelets: Iterable[Pipelet]) -> list[dict[str, Any]]:
    return [
        {
            "name": pipelet.name,
            "event": pipelet.event,
            "code": pipelet.code,
        }
        for pipelet in pipelets
    ]


def _serialize_workflows(workflows: Iterable[Workflow]) -> list[dict[str, Any]]:
    return [
        {
            "name": workflow.name,
            "event": workflow.event,
            "graph_json": workflow.graph_json,
        }
        for workflow in workflows
    ]


@bp.get("/export")
@require_token()
def export_configuration() -> tuple[object, int]:
    """Return a snapshot of all pipelets and workflows."""

    pipelets = Pipelet.query.order_by(Pipelet.name.asc()).all()
    workflows = Workflow.query.order_by(Workflow.name.asc()).all()
    payload = {
        "version": 1,
        "pipelets": _serialize_pipelets(pipelets),
        "workflows": _serialize_workflows(workflows),
    }
    return jsonify(payload), HTTPStatus.OK


def _validate_pipelets_for_import(
    payload: list[Any],
) -> tuple[list[dict[str, Any]], tuple[list[str], int]]:
    """Validate and normalise the pipelet section of an import payload."""

    normalised: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            return normalised, ([f"pipelets[{index}] must be an object"], HTTPStatus.BAD_REQUEST)
        data, errors = _validate_pipelet_payload(item)
        if errors:
            return normalised, (errors, HTTPStatus.BAD_REQUEST)
        normalised.append(data)
    return normalised, ([], HTTPStatus.OK)


def _is_workflow_event_conflict(event: str | None, workflow_id: int | None = None) -> bool:
    if event is None:
        return False
    query = Workflow.query.filter(Workflow.event == event)
    if workflow_id is not None:
        query = query.filter(Workflow.id != workflow_id)
    return db.session.query(query.exists()).scalar()  # type: ignore[arg-type]


def _validate_workflows_for_import(
    payload: list[Any],
) -> tuple[list[dict[str, Any]], tuple[list[str], int]]:
    normalised: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            return normalised, ([f"workflows[{index}] must be an object"], HTTPStatus.BAD_REQUEST)

        name = (item.get("name") or "").strip()
        if not name:
            return normalised, (["name is required"], HTTPStatus.BAD_REQUEST)

        graph_text, graph_errors = _normalize_graph(
            item.get("graph_json"), allow_default=True
        )
        if graph_errors:
            return normalised, (graph_errors, HTTPStatus.BAD_REQUEST)

        event_value, event_errors = _normalize_event(item.get("event"))
        if event_errors:
            return normalised, (event_errors, HTTPStatus.BAD_REQUEST)

        normalised.append(
            {
                "name": name,
                "graph_json": graph_text,
                "event": event_value,
            }
        )
    return normalised, ([], HTTPStatus.OK)


@bp.post("/import")
@require_token(role="admin")
def import_configuration() -> tuple[object, int]:
    """Import pipelets and workflows from a snapshot."""

    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), HTTPStatus.BAD_REQUEST

    overwrite_flag = request.args.get("overwrite", "false").lower()
    overwrite = overwrite_flag in {"1", "true", "yes"}

    pipelet_items = payload.get("pipelets", [])
    workflow_items = payload.get("workflows", [])

    if not isinstance(pipelet_items, list):
        return jsonify({"error": "pipelets must be a list"}), HTTPStatus.BAD_REQUEST
    if not isinstance(workflow_items, list):
        return jsonify({"error": "workflows must be a list"}), HTTPStatus.BAD_REQUEST

    pipelets, (pipelet_errors, pipelet_status) = _validate_pipelets_for_import(pipelet_items)
    if pipelet_errors:
        return jsonify({"errors": pipelet_errors}), pipelet_status

    workflows, (workflow_errors, workflow_status) = _validate_workflows_for_import(
        workflow_items
    )
    if workflow_errors:
        return jsonify({"errors": workflow_errors}), workflow_status

    created = 0
    updated = 0

    for data in pipelets:
        existing = Pipelet.query.filter_by(name=data["name"]).first()
        if existing is not None:
            if not overwrite:
                return (
                    jsonify({"error": f"pipelet {data['name']} already exists"}),
                    HTTPStatus.CONFLICT,
                )
            existing.event = data["event"]
            existing.code = data["code"]
            updated += 1
        else:
            pipelet = Pipelet(**data)
            db.session.add(pipelet)
            created += 1

    for data in workflows:
        existing = Workflow.query.filter_by(name=data["name"]).first()
        if existing is not None:
            if not overwrite:
                return (
                    jsonify({"error": f"workflow {data['name']} already exists"}),
                    HTTPStatus.CONFLICT,
                )
            if _is_workflow_event_conflict(data["event"], existing.id):
                return (
                    jsonify({"error": "event ist bereits zugeordnet"}),
                    HTTPStatus.CONFLICT,
                )
            existing.graph_json = data["graph_json"]
            existing.event = data["event"]
            updated += 1
        else:
            if _is_workflow_event_conflict(data["event"], None):
                return (
                    jsonify({"error": "event ist bereits zugeordnet"}),
                    HTTPStatus.CONFLICT,
                )
            workflow = Workflow(**data)
            db.session.add(workflow)
            created += 1

    db.session.commit()

    return jsonify({"created": created, "updated": updated}), HTTPStatus.OK
