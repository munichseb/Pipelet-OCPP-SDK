"""REST API endpoints for storing and retrieving workflows."""

from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from ..extensions import db
from ..models.workflow import Workflow

bp = Blueprint("workflows", __name__)

MAX_GRAPH_BYTES = 500_000


def _serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    """Return a JSON serialisable representation of a workflow."""

    try:
        graph = json.loads(workflow.graph_json)
    except (TypeError, ValueError):
        graph = {}
    return {"id": workflow.id, "name": workflow.name, "graph_json": graph}


def _normalize_graph(value: Any, *, allow_default: bool = False) -> tuple[str, list[str]]:
    """Validate and serialise the graph payload, returning errors if present."""

    errors: list[str] = []

    if value is None:
        if allow_default:
            return json.dumps({}), errors
        errors.append("graph_json is required")
        return "", errors

    if isinstance(value, str):
        if not value.strip():
            errors.append("graph_json darf nicht leer sein")
            return "", errors
        graph_text = value
    else:
        try:
            graph_text = json.dumps(value)
        except (TypeError, ValueError):
            errors.append("graph_json muss serialisierbar sein")
            return "", errors

    if len(graph_text.encode("utf-8")) > MAX_GRAPH_BYTES:
        errors.append("graph_json überschreitet die maximale Größe")

    return graph_text, errors


def _is_name_unique(name: str, workflow_id: int | None = None) -> bool:
    """Check whether the workflow name is unique."""

    query = Workflow.query.filter(func.lower(Workflow.name) == name.lower())
    if workflow_id is not None:
        query = query.filter(Workflow.id != workflow_id)
    return not db.session.query(query.exists()).scalar()


@bp.post("/workflows")
def create_workflow() -> tuple[object, int]:
    payload = request.get_json(silent=True, force=True) or {}
    name = (payload.get("name") or "").strip()

    if not name:
        return jsonify({"error": "name ist erforderlich"}), HTTPStatus.BAD_REQUEST

    if not _is_name_unique(name):
        return jsonify({"error": "workflow mit diesem Namen existiert bereits"}), HTTPStatus.CONFLICT

    graph_text, errors = _normalize_graph(payload.get("graph_json"), allow_default=True)
    if errors:
        return jsonify({"errors": errors}), HTTPStatus.BAD_REQUEST

    workflow = Workflow(name=name, graph_json=graph_text)
    db.session.add(workflow)
    db.session.commit()

    return jsonify(_serialize_workflow(workflow)), HTTPStatus.CREATED


@bp.get("/workflows")
def list_workflows() -> tuple[object, int]:
    workflows = Workflow.query.order_by(Workflow.created_at.desc()).all()
    return jsonify([{"id": wf.id, "name": wf.name} for wf in workflows]), HTTPStatus.OK


@bp.get("/workflows/<int:workflow_id>")
def get_workflow(workflow_id: int) -> tuple[object, int]:
    workflow = Workflow.query.get_or_404(workflow_id)
    return jsonify(_serialize_workflow(workflow)), HTTPStatus.OK


@bp.put("/workflows/<int:workflow_id>")
def update_workflow(workflow_id: int) -> tuple[object, int]:
    workflow = Workflow.query.get_or_404(workflow_id)
    payload = request.get_json(silent=True, force=True) or {}

    name = payload.get("name")
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify({"error": "name darf nicht leer sein"}), HTTPStatus.BAD_REQUEST
        if not _is_name_unique(name, workflow_id):
            return jsonify({"error": "workflow mit diesem Namen existiert bereits"}), HTTPStatus.CONFLICT
        workflow.name = name

    graph_text, errors = _normalize_graph(payload.get("graph_json"))
    if errors:
        return jsonify({"errors": errors}), HTTPStatus.BAD_REQUEST

    workflow.graph_json = graph_text
    db.session.commit()

    return jsonify(_serialize_workflow(workflow)), HTTPStatus.OK
